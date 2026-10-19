import hashlib
import json

from app.pricing import token_cost_micros
from app.repositories import usage_repo


class IdempotencyConflict(Exception):
    pass


def hash_request(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def record(conn, tenant_id: int, idempotency_key: str, payload: dict) -> dict:
    input_t = payload.get("input_tokens", 0)
    cached_t = payload.get("cached_input_tokens", 0)
    output_t = payload.get("output_tokens", 0)
    reasoning_t = payload.get("reasoning_tokens", 0)
    cost = token_cost_micros(input_t, cached_t, output_t, reasoning_t)
    req_hash = hash_request(payload)

    row = usage_repo.insert_event(
        conn,
        tenant_id=tenant_id,
        type="ai_tokens",
        quantity=input_t + output_t + reasoning_t,
        input_tokens=input_t,
        cached_input_tokens=cached_t,
        output_tokens=output_t,
        reasoning_tokens=reasoning_t,
        cost_micros=cost,
        request_hash=req_hash,
        idempotency_key=idempotency_key,
    )
    if row is not None:
        return {"event_id": row.id, "cost_micros": cost, "replayed": False}

    existing = usage_repo.get_event(conn, tenant_id, idempotency_key)
    if existing.request_hash != req_hash:
        raise IdempotencyConflict()
    return {"event_id": existing.id, "cost_micros": existing.cost_micros, "replayed": True}