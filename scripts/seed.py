from sqlalchemy import text

from app.db import engine

with engine.begin() as c:
    c.execute(text(
        "INSERT INTO tenants (id, name, plan_id) VALUES (1, 'acme', 1) ON CONFLICT (id) DO NOTHING"))
print("seeded tenant 1 on the free plan")