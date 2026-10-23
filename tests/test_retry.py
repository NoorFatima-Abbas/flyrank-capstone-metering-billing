import json

from sqlalchemy import text

from app import jobs
from app.db import engine
from app.repositories import stripe_repo


def test_failed_event_is_retried_and_resolved():
    with engine.begin() as c:
        c.execute(text("DELETE FROM failed_webhooks"))
        c.execute(text("DELETE FROM subscriptions"))
        c.execute(text("DELETE FROM stripe_events"))
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
        c.execute(text("INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', 1)"))
        event = {"id": "evt_retry", "type": "checkout.session.completed",
                 "data": {"object": {"client_reference_id": "1", "subscription": "sub_r"}}}
        stripe_repo.record_failure(c, "evt_retry", json.dumps(event), "simulated failure")
    assert jobs.retry_failed_once() == 1
    with engine.begin() as c:
        plan = c.execute(text("SELECT p.name FROM tenants t JOIN plans p ON p.id = t.plan_id WHERE t.id = 1")).scalar()
        resolved = c.execute(text("SELECT resolved FROM failed_webhooks WHERE event_id = 'evt_retry'")).scalar()
    assert plan == "pro" and resolved is True