"""Add license match fields for suggested matches.

Revision ID: 011
Revises: 010
Create Date: 2024-01-30

Note: No employee_aliases table - GDPR compliance prevents storing
private email addresses. Instead, we only store match suggestions
on the license itself for manual review.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add match fields to licenses table
    # These fields support the suggested match workflow without storing private emails
    op.add_column('licenses', sa.Column(
        'suggested_employee_id',
        postgresql.UUID(as_uuid=True),
        nullable=True
    ))
    op.add_column('licenses', sa.Column(
        'match_confidence',
        sa.Float(),
        nullable=True,
        comment='Confidence score 0.0-1.0 for suggested matches'
    ))
    op.add_column('licenses', sa.Column(
        'match_status',
        sa.String(50),
        nullable=True,
        comment='auto_matched, suggested, confirmed, rejected, external_guest, external_review'
    ))
    op.add_column('licenses', sa.Column(
        'match_method',
        sa.String(50),
        nullable=True,
        comment='exact_email, local_part, fuzzy_name'
    ))
    op.add_column('licenses', sa.Column(
        'match_reviewed_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))
    op.add_column('licenses', sa.Column(
        'match_reviewed_by',
        postgresql.UUID(as_uuid=True),
        nullable=True
    ))

    # Add foreign key for suggested_employee_id
    op.create_foreign_key(
        'fk_licenses_suggested_employee',
        'licenses', 'employees',
        ['suggested_employee_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add foreign key for match_reviewed_by
    op.create_foreign_key(
        'fk_licenses_match_reviewed_by',
        'licenses', 'admin_users',
        ['match_reviewed_by'], ['id'],
        ondelete='SET NULL'
    )

    # Create index for suggested matches
    op.create_index('idx_licenses_suggested_employee', 'licenses', ['suggested_employee_id'])
    op.create_index('idx_licenses_match_status', 'licenses', ['match_status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_licenses_match_status', table_name='licenses')
    op.drop_index('idx_licenses_suggested_employee', table_name='licenses')

    # Drop foreign keys
    op.drop_constraint('fk_licenses_match_reviewed_by', 'licenses', type_='foreignkey')
    op.drop_constraint('fk_licenses_suggested_employee', 'licenses', type_='foreignkey')

    # Drop columns from licenses
    op.drop_column('licenses', 'match_reviewed_by')
    op.drop_column('licenses', 'match_reviewed_at')
    op.drop_column('licenses', 'match_method')
    op.drop_column('licenses', 'match_status')
    op.drop_column('licenses', 'match_confidence')
    op.drop_column('licenses', 'suggested_employee_id')
