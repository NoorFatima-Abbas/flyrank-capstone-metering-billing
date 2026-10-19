import json

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.db import engine
from app.repositories import stripe_repo
from app.services import webhook_service

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
    with engine.begin() as conn:
        if not stripe_repo.claim_event(conn, event["id"], event["type"]):
            return {"status": "duplicate"}
        webhook_service.apply(conn, event)
    return {"status": "processed"}