"""Add CASCADE DELETE to licenses provider_id foreign key.

Revision ID: 005
Revises: 004
Create Date: 2026-01-30

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint("licenses_provider_id_fkey", "licenses", type_="foreignkey")

    # Re-create with CASCADE DELETE
    op.create_foreign_key(
        "licenses_provider_id_fkey",
        "licenses",
        "providers",
        ["provider_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop the CASCADE constraint
    op.drop_constraint("licenses_provider_id_fkey", "licenses", type_="foreignkey")

    # Re-create without CASCADE
    op.create_foreign_key(
        "licenses_provider_id_fkey",
        "licenses",
        "providers",
        ["provider_id"],
        ["id"],
    )
