from sqlalchemy import text


def claim_event(conn, event_id: str, event_type: str) -> bool:
    row = conn.execute(
        text("INSERT INTO stripe_events (event_id, type) VALUES (:i, :t) "
             "ON CONFLICT (event_id) DO NOTHING RETURNING event_id"),
        {"i": event_id, "t": event_type},
    ).first()
    return row is not None


def set_plan(conn, tenant_id: int, plan_name: str, status: str):
    conn.execute(
        text("UPDATE tenants SET plan_id = (SELECT id FROM plans WHERE name = :p), "
             "subscription_status = :s WHERE id = :id"),
        {"p": plan_name, "s": status, "id": tenant_id},
    )


def find_tenant_by_customer(conn, customer_id: str):
    row = conn.execute(
        text("SELECT id FROM tenants WHERE stripe_customer_id = :c"), {"c": customer_id}
    ).first()
    return row.id if row else None


def upsert_subscription(conn, tenant_id: int, subscription_id: str, status: str):
    conn.execute(
        text("INSERT INTO subscriptions (tenant_id, stripe_subscription_id, status) "
             "VALUES (:t, :s, :st) ON CONFLICT (stripe_subscription_id) "
             "DO UPDATE SET status = EXCLUDED.status, tenant_id = EXCLUDED.tenant_id"),
        {"t": tenant_id, "s": subscription_id, "st": status},
    )

def record_failure(conn, event_id: str, payload: str, error: str):
    conn.execute(
        text("INSERT INTO failed_webhooks (event_id, payload, last_error) VALUES (:i, :p, :e) "
             "ON CONFLICT (event_id) DO UPDATE SET last_error = EXCLUDED.last_error"),
        {"i": event_id, "p": payload, "e": error},
    )


def pending_failures(conn, max_attempts: int):
    return conn.execute(
        text("SELECT event_id, payload, attempts FROM failed_webhooks "
             "WHERE resolved = false AND attempts < :m ORDER BY created_at"),
        {"m": max_attempts},
    ).fetchall()


def mark_resolved(conn, event_id: str):
    conn.execute(text("UPDATE failed_webhooks SET resolved = true WHERE event_id = :i"), {"i": event_id})


def bump_attempt(conn, event_id: str, error: str):
    conn.execute(
        text("UPDATE failed_webhooks SET attempts = attempts + 1, last_error = :e WHERE event_id = :i"),
        {"i": event_id, "e": error},
    )