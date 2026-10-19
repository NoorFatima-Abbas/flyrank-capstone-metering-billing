import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.main import app

client = TestClient(app)
SECRET = "whsec_test"


def signed(payload: dict, secret: str = SECRET):
    body = json.dumps(payload).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"}


def completed_event(event_id: str):
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": "1", "subscription": "sub_test_1", "customer": "cus_test_1"}},
    }


def clean():
    with engine.begin() as c:
        c.execute(text("DELETE FROM subscriptions"))
        c.execute(text("DELETE FROM stripe_events"))
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    clean()
    with engine.begin() as c:
        c.execute(text("INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', 1)"))
    yield
    clean()


def plan_of_tenant():
    with engine.begin() as c:
        return c.execute(text("SELECT p.name FROM tenants t JOIN plans p ON p.id = t.plan_id WHERE t.id = 1")).scalar()


def test_forged_signature_returns_400_and_changes_nothing(setup):
    body, headers = signed(completed_event("evt_forged"), secret="whsec_wrong")
    r = client.post("/webhooks/stripe", content=body, headers=headers)
    assert r.status_code == 400
    assert plan_of_tenant() == "free"
    with engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM stripe_events")).scalar() == 0


def test_valid_event_flips_free_to_pro_and_usage_shows_new_limits(setup):
    body, headers = signed(completed_event("evt_1"))
    r = client.post("/webhooks/stripe", content=body, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "processed"
    assert plan_of_tenant() == "pro"
    usage = client.get("/usage", headers={"X-Tenant-Id": "1"}).json()
    assert usage["plan"] == "pro"
    assert usage["api_calls"]["limit"] == 50000


def test_replayed_event_is_processed_once(setup):
    body, headers = signed(completed_event("evt_2"))
    first = client.post("/webhooks/stripe", content=body, headers=headers)
    second = client.post("/webhooks/stripe", content=body, headers=headers)
    assert first.json()["status"] == "processed"
    assert second.status_code == 200 and second.json()["status"] == "duplicate"
    with engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM stripe_events WHERE event_id = 'evt_2'")).scalar() == 1