"""Add cost_snapshots table for historical cost tracking.

Revision ID: 010
Revises: 009
Create Date: 2026-01-30

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cost_snapshots table
    op.create_table(
        "cost_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("snapshot_date", sa.Date, nullable=False, index=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("providers.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("license_count", sa.Integer, nullable=False),
        sa.Column("active_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unassigned_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("breakdown", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("snapshot_date", "provider_id", name="uq_cost_snapshot_date_provider"),
    )

    # Create composite index for efficient queries by date range and provider
    op.create_index(
        "ix_cost_snapshots_date_provider",
        "cost_snapshots",
        ["snapshot_date", "provider_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cost_snapshots_date_provider")
    op.drop_table("cost_snapshots")
