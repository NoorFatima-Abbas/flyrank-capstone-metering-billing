from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import engine
from app.services import meter_service

router = APIRouter()


class GenerateRequest(BaseModel):
    input_tokens: int = Field(0, ge=0)
    cached_input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    reasoning_tokens: int = Field(0, ge=0)


def seconds_until_next_month() -> int:
    now = datetime.now(timezone.utc)
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return int((datetime(year, month, 1, tzinfo=timezone.utc) - now).total_seconds())


@router.post("/generate")
def generate(
    body: GenerateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    tenant_id: int = Header(..., alias="X-Tenant-Id"),
):
    if body.cached_input_tokens > body.input_tokens:
        raise HTTPException(422, "cached_input_tokens cannot exceed input_tokens")
    try:
        with engine.begin() as conn:
            result = meter_service.record(conn, tenant_id, idempotency_key, body.model_dump())
    except meter_service.TenantNotFound:
        raise HTTPException(404, "tenant not found")
    except meter_service.IdempotencyConflict:
        raise HTTPException(422, "idempotency key was already used with a different request body")
    except meter_service.PaymentRequired:
        raise HTTPException(402, "subscription is not active; update payment to continue")
    except meter_service.QuotaExceeded as e:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(seconds_until_next_month())},
            content={
                "error": "quota_exceeded",
                "resource": e.resource,
                "used": e.used,
                "requested": e.requested,
                "limit": e.limit,
                "message": f"Monthly {e.resource} quota reached. Upgrade to Pro or wait for the next cycle.",
            },
        )
    return {
        "event_id": result["event_id"],
        "cost_micros": result["cost_micros"],
        "cost_usd": f"{result['cost_micros'] / 1_000_000:.6f}",
        "replayed": result["replayed"],
    }