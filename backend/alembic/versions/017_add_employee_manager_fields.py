"""Add manager fields to employees table.

Revision ID: 017
Revises: 016
Create Date: 2026-02-01

This migration adds manager relationship fields to employees:
- manager_email: Email of the manager from HRIS
- manager_id: FK to employees table (resolved after sync)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add manager fields to employees table."""
    # Add manager_email column
    op.add_column(
        "employees",
        sa.Column("manager_email", sa.String(255), nullable=True),
    )

    # Add manager_id column with FK to employees
    op.add_column(
        "employees",
        sa.Column(
            "manager_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add index for manager_id lookups
    op.create_index(
        "idx_employees_manager_id",
        "employees",
        ["manager_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove manager fields from employees table."""
    op.drop_index("idx_employees_manager_id", table_name="employees")
    op.drop_column("employees", "manager_id")
    op.drop_column("employees", "manager_email")
