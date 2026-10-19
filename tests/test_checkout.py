from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)


def test_checkout_unknown_tenant_returns_404():
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
    r = client.post("/checkout", headers={"X-Tenant-Id": "999"})
    assert r.status_code == 404