from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)


def reset(plan_id=1):
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
        c.execute(text("INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', :p)"), {"p": plan_id})


def test_usage_matches_pinned_pricing():
    reset(plan_id=2)
    h = {"Idempotency-Key": "u-1", "X-Tenant-Id": "1"}
    body = {"input_tokens": 1_000_000, "cached_input_tokens": 400_000,
            "output_tokens": 100_000, "reasoning_tokens": 50_000}
    r = client.post("/generate", json=body, headers=h)
    assert r.status_code == 200
    assert r.json()["cost_micros"] == 585_000
    u = client.get("/usage", headers={"X-Tenant-Id": "1"}).json()
    assert u["api_calls"] == {"used": 1, "limit": 50000}
    assert u["cost_micros"]["ai_tokens"] == 585_000
    assert u["cost_micros"]["total"] == 586_000


def test_http_replay_returns_same_response():
    reset()
    h = {"Idempotency-Key": "u-2", "X-Tenant-Id": "1"}
    first = client.post("/generate", json={"input_tokens": 100}, headers=h).json()
    second = client.post("/generate", json={"input_tokens": 100}, headers=h).json()
    assert second["replayed"] is True
    assert second["event_id"] == first["event_id"]


def test_http_429_has_retry_after_and_message():
    reset()
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO usage_events (tenant_id, type, quantity, request_hash, idempotency_key) "
            "SELECT 1, 'ai_tokens', 0, 'x', 's-' || g FROM generate_series(1, 1000) g"))
    r = client.post("/generate", json={"input_tokens": 1},
                    headers={"Idempotency-Key": "over", "X-Tenant-Id": "1"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert r.json()["used"] == 1000 and r.json()["limit"] == 1000