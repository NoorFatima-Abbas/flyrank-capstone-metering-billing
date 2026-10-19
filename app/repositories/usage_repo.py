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