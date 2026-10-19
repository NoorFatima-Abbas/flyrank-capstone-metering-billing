from fastapi import APIRouter, Header, HTTPException

from app.db import engine
from app.services import usage_service

router = APIRouter()


@router.get("/usage")
def get_usage(tenant_id: int = Header(..., alias="X-Tenant-Id")):
    with engine.begin() as conn:
        result = usage_service.rollup(conn, tenant_id)
    if result is None:
        raise HTTPException(404, "tenant not found")
    return result