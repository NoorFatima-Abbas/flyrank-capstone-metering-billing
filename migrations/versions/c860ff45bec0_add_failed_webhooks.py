"""add failed webhooks

Revision ID: c860ff45bec0
Revises: 1bc255a70019
Create Date: 2026-10-23 20:58:26.910663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c860ff45bec0'
down_revision: Union[str, Sequence[str], None] = '1bc255a70019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   op.create_table(
        "failed_webhooks",
        sa.Column("event_id", sa.String(100), primary_key=True),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("last_error", sa.Text),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
   pass


def downgrade() -> None:
    op.drop_table("failed_webhooks")
    pass
