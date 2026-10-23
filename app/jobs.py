import json
import logging
import threading
import time

from app.db import engine
from app.repositories import stripe_repo
from app.services import webhook_service

log = logging.getLogger("webhook-retry")
MAX_ATTEMPTS = 5


def process_event(conn, event: dict) -> str:
    if not stripe_repo.claim_event(conn, event["id"], event["type"]):
        return "duplicate"
    webhook_service.apply(conn, event)
    return "processed"


def retry_failed_once() -> int:
    with engine.begin() as conn:
        rows = stripe_repo.pending_failures(conn, MAX_ATTEMPTS)
    done = 0
    for row in rows:
        try:
            with engine.begin() as conn:
                process_event(conn, json.loads(row.payload))
                stripe_repo.mark_resolved(conn, row.event_id)
            done += 1
        except Exception as exc:
            with engine.begin() as conn:
                stripe_repo.bump_attempt(conn, row.event_id, str(exc))
            if row.attempts + 1 >= MAX_ATTEMPTS:
                log.error("ALERT: webhook %s failed permanently after %d attempts: %s",
                          row.event_id, MAX_ATTEMPTS, exc)
    return done


def start_retry_loop(interval_seconds: int = 60):
    def loop():
        while True:
            time.sleep(interval_seconds)
            try:
                retry_failed_once()
            except Exception:
                log.exception("retry loop error")

    threading.Thread(target=loop, daemon=True).start()