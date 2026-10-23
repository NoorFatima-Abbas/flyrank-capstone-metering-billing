import json

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.db import engine
from app.jobs import process_event
from app.repositories import stripe_repo

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(400, "missing signature")
    try:
        stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "invalid signature")

    event = json.loads(payload)
    try:
        with engine.begin() as conn:
            status = process_event(conn, event)
        return {"status": status}
    except Exception as exc:
        with engine.begin() as conn:
            stripe_repo.record_failure(conn, event["id"], payload.decode(), str(exc))
        return {"status": "queued_for_retry"}