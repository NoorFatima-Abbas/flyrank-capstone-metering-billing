"""create core tables

Revision ID: 1bc255a70019
Revises: 
Create Date: 2026-10-19 05:30:10.203367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1bc255a70019'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("api_calls_limit", sa.BigInteger, nullable=False),
        sa.Column("ai_tokens_limit", sa.BigInteger, nullable=False),
    )
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("subscription_status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.String(100), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.BigInteger, nullable=False),
        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("cached_input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("reasoning_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_usage_tenant_idem"),
    )
    op.create_index("ix_usage_tenant_created", "usage_events", ["tenant_id", "created_at"])
    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(100), primary_key=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        "INSERT INTO plans (name, api_calls_limit, ai_tokens_limit) VALUES "
        "('free', 1000, 100000), ('pro', 50000, 5000000)"
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_index("ix_usage_tenant_created", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_table("subscriptions")
    op.drop_table("tenants")
    op.drop_table("plans")