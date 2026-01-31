"""Add user notification preferences table.

Revision ID: 009
Revises: 008
Create Date: 2026-01-30

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_notification_preferences table
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean, default=True, nullable=False, server_default="true"),
        sa.Column("slack_dm", sa.Boolean, default=False, nullable=False, server_default="false"),
        sa.Column("slack_channel", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "event_type", name="uq_user_notification_pref"),
    )

    # Create index for efficient lookups by event type
    op.create_index(
        "ix_user_notification_preferences_event_type",
        "user_notification_preferences",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_notification_preferences_event_type")
    op.drop_table("user_notification_preferences")
