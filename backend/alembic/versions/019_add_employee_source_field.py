"""Add employee source field for manual HRIS support.

Revision ID: 019
Revises: 018
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source column to employees table
    # Values: 'hibob', 'personio', 'manual'
    op.add_column(
        "employees",
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default="hibob",
        ),
    )

    # Create index for filtering by source
    op.create_index(
        "ix_employees_source",
        "employees",
        ["source"],
    )

    # Update hibob_id to be nullable for manual employees
    # Manual employees will have a generated UUID as hibob_id
    # but the constraint needs to stay unique


def downgrade() -> None:
    op.drop_index("ix_employees_source", table_name="employees")
    op.drop_column("employees", "source")
