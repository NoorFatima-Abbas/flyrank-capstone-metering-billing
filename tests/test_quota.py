from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from app.db import engine
from app.services import meter_service

SEED_999 = text(
    "INSERT INTO usage_events (tenant_id, type, quantity, request_hash, idempotency_key) "
    "SELECT 1, 'ai_tokens', 0, 'x', 'seed-' || g FROM generate_series(1, 999) g"
)


@pytest.fixture
def clean():
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
        c.execute(text("INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', 1)"))
        c.execute(SEED_999)


def count_events():
    with engine.begin() as c:
        return c.execute(text("SELECT count(*) FROM usage_events")).scalar()


def test_boundary_exact_limit_allowed_then_blocked(clean):
    with engine.begin() as c:
        ok = meter_service.record(c, 1, "b-1000", {"input_tokens": 10})
    assert ok["replayed"] is False
    with pytest.raises(meter_service.QuotaExceeded) as exc:
        with engine.begin() as c:
            meter_service.record(c, 1, "b-1001", {"input_tokens": 10})
    assert exc.value.used == 1000 and exc.value.limit == 1000
    assert count_events() == 1000


def test_replay_at_limit_returns_original(clean):
    with engine.begin() as c:
        first = meter_service.record(c, 1, "b-1000", {"input_tokens": 10})
    with engine.begin() as c:
        again = meter_service.record(c, 1, "b-1000", {"input_tokens": 10})
    assert again["replayed"] is True
    assert again["event_id"] == first["event_id"]


def test_lapsed_subscription_returns_payment_required(clean):
    with engine.begin() as c:
        c.execute(text("UPDATE tenants SET subscription_status = 'past_due' WHERE id = 1"))
    with pytest.raises(meter_service.PaymentRequired):
        with engine.begin() as c:
            meter_service.record(c, 1, "late-1", {"input_tokens": 10})


def test_concurrent_requests_at_999_only_one_succeeds(clean):
    def attempt(i):
        try:
            with engine.begin() as c:
                meter_service.record(c, 1, f"race-{i}", {"input_tokens": 10})
            return True
        except meter_service.QuotaExceeded:
            return False

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(attempt, range(5)))
    assert results.count(True) == 1
    assert count_events() == 1000