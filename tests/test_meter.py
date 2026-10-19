import pytest
from sqlalchemy import text

from app.db import engine
from app.services import meter_service
from app.pricing import token_cost_micros


@pytest.fixture
def conn():
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
        c.execute(text("INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', 1)"))
    with engine.begin() as c:
        yield c


def test_same_key_twice_creates_one_event(conn):
    payload = {"input_tokens": 1000, "output_tokens": 500}
    first = meter_service.record(conn, 1, "key-1", payload)
    second = meter_service.record(conn, 1, "key-1", payload)
    count = conn.execute(text("SELECT count(*) FROM usage_events")).scalar()
    assert count == 1
    assert first["replayed"] is False
    assert second["replayed"] is True
    assert first["event_id"] == second["event_id"]


def test_same_key_different_body_conflicts(conn):
    meter_service.record(conn, 1, "key-2", {"input_tokens": 10})
    with pytest.raises(meter_service.IdempotencyConflict):
        meter_service.record(conn, 1, "key-2", {"input_tokens": 99})


def test_cached_and_reasoning_pricing():
    assert token_cost_micros(1_000_000, 400_000, 100_000, 50_000) == 585_000