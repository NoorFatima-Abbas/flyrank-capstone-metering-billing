from sqlalchemy import text

INSERT_SQL = text("""
INSERT INTO usage_events
 (tenant_id, type, quantity, input_tokens, cached_input_tokens, output_tokens,
  reasoning_tokens, cost_micros, request_hash, idempotency_key)
VALUES
 (:tenant_id, :type, :quantity, :input_tokens, :cached_input_tokens, :output_tokens,
  :reasoning_tokens, :cost_micros, :request_hash, :idempotency_key)
ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
RETURNING id
""")

GET_SQL = text("""
SELECT id, quantity, cost_micros, request_hash
FROM usage_events
WHERE tenant_id = :tenant_id AND idempotency_key = :idempotency_key
""")


def insert_event(conn, **params):
    return conn.execute(INSERT_SQL, params).first()


def get_event(conn, tenant_id: int, idempotency_key: str):
    return conn.execute(GET_SQL, {"tenant_id": tenant_id, "idempotency_key": idempotency_key}).first()

LOCK_TENANT_SQL = text("""
SELECT t.id, t.subscription_status, p.api_calls_limit, p.ai_tokens_limit
FROM tenants t JOIN plans p ON p.id = t.plan_id
WHERE t.id = :tenant_id
FOR UPDATE OF t
""")

USAGE_SQL = text("""
SELECT count(*) AS calls, COALESCE(sum(quantity), 0) AS tokens
FROM usage_events
WHERE tenant_id = :tenant_id AND created_at >= date_trunc('month', now())
""")


def lock_tenant(conn, tenant_id: int):
    return conn.execute(LOCK_TENANT_SQL, {"tenant_id": tenant_id}).first()


def get_usage(conn, tenant_id: int):
    row = conn.execute(USAGE_SQL, {"tenant_id": tenant_id}).first()
    return int(row.calls), int(row.tokens)