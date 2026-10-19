from fastapi import APIRouter, Header, HTTPException

from app.db import engine
from app.services import billing_service

router = APIRouter()


@router.post("/checkout")
def checkout(tenant_id: int = Header(..., alias="X-Tenant-Id")):
    try:
        with engine.begin() as conn:
            url = billing_service.create_checkout(conn, tenant_id)
    except billing_service.TenantNotFound:
        raise HTTPException(404, "tenant not found")
    return {"checkout_url": url}