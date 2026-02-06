"""Add import_jobs table for tracking license imports.

Revision ID: 029
Revises: 028
Create Date: 2026-02-06

This migration adds the import_jobs table to track CSV import jobs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create import_jobs table."""
    op.create_table(
        "import_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_mapping", JSONB(), nullable=False),
        sa.Column("options", JSONB(), nullable=False),
        sa.Column("error_details", JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Create indexes
    op.create_index("idx_import_jobs_provider", "import_jobs", ["provider_id"])
    op.create_index("idx_import_jobs_status", "import_jobs", ["status"])
    op.create_index("idx_import_jobs_created_by", "import_jobs", ["created_by"])
    op.create_index("idx_import_jobs_created_at", "import_jobs", ["created_at"])

    # Add licenses.import permission if not exists
    op.execute("""
        INSERT INTO permissions (id, code, name, description, category)
        VALUES (
            gen_random_uuid(),
            'licenses.import',
            'Import Licenses',
            'Import licenses from CSV files',
            'licenses'
        )
        ON CONFLICT (code) DO NOTHING
    """)

    # Add permission to admin role if it exists
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'admin' AND p.code = 'licenses.import'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    """Drop import_jobs table."""
    # Remove permission from roles
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE code = 'licenses.import'
        )
    """)

    # Remove permission
    op.execute("DELETE FROM permissions WHERE code = 'licenses.import'")

    # Drop indexes
    op.drop_index("idx_import_jobs_created_at", table_name="import_jobs")
    op.drop_index("idx_import_jobs_created_by", table_name="import_jobs")
    op.drop_index("idx_import_jobs_status", table_name="import_jobs")
    op.drop_index("idx_import_jobs_provider", table_name="import_jobs")

    # Drop table
    op.drop_table("import_jobs")
