import pytest
from sqlalchemy import text

from app.db import engine


@pytest.fixture(autouse=True)
def clean_db():
    with engine.begin() as c:
        c.execute(text("DELETE FROM failed_webhooks"))
        c.execute(text("DELETE FROM subscriptions"))
        c.execute(text("DELETE FROM stripe_events"))
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM tenants"))
    yield