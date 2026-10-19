import hashlib
import json

from app.pricing import token_cost_micros
from app.repositories import usage_repo

ACTIVE_STATUSES = ("active", "trialing")


class IdempotencyConflict(Exception):
    pass


class TenantNotFound(Exception):
    pass


class PaymentRequired(Exception):
    pass


class QuotaExceeded(Exception):
    def __init__(self, resource: str, used: int, requested: int, limit: int):
        self.resource = resource
        self.used = used
        self.requested = requested
        self.limit = limit


def hash_request(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def record(conn, tenant_id: int, idempotency_key: str, payload: dict) -> dict:
    tenant = usage_repo.lock_tenant(conn, tenant_id)
    if tenant is None:
        raise TenantNotFound()

    input_t = payload.get("input_tokens", 0)
    cached_t = payload.get("cached_input_tokens", 0)
    output_t = payload.get("output_tokens", 0)
    reasoning_t = payload.get("reasoning_tokens", 0)
    cost = token_cost_micros(input_t, cached_t, output_t, reasoning_t)
    req_hash = hash_request(payload)

    existing = usage_repo.get_event(conn, tenant_id, idempotency_key)
    if existing is not None:
        if existing.request_hash != req_hash:
            raise IdempotencyConflict()
        return {"event_id": existing.id, "cost_micros": existing.cost_micros, "replayed": True}

    if tenant.subscription_status not in ACTIVE_STATUSES:
        raise PaymentRequired()

    quantity = input_t + output_t + reasoning_t
    calls_used, tokens_used = usage_repo.get_usage(conn, tenant_id)
    if calls_used + 1 > tenant.api_calls_limit:
        raise QuotaExceeded("api_calls", calls_used, 1, tenant.api_calls_limit)
    if tokens_used + quantity > tenant.ai_tokens_limit:
        raise QuotaExceeded("ai_tokens", tokens_used, quantity, tenant.ai_tokens_limit)

    row = usage_repo.insert_event(
        conn,
        tenant_id=tenant_id,
        type="ai_tokens",
        quantity=quantity,
        input_tokens=input_t,
        cached_input_tokens=cached_t,
        output_tokens=output_t,
        reasoning_tokens=reasoning_t,
        cost_micros=cost,
        request_hash=req_hash,
        idempotency_key=idempotency_key,
    )
    return {"event_id": row.id, "cost_micros": cost, "replayed": False}