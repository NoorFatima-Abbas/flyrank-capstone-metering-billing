from sqlalchemy import text


def get_tenant(conn, tenant_id: int):
    return conn.execute(
        text("SELECT id, name, stripe_customer_id FROM tenants WHERE id = :id"),
        {"id": tenant_id},
    ).first()


def set_customer_id(conn, tenant_id: int, customer_id: str):
    conn.execute(
        text("UPDATE tenants SET stripe_customer_id = :c WHERE id = :id"),
        {"c": customer_id, "id": tenant_id},
    )