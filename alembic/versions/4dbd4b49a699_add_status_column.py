"""Add status column

Revision ID: 4dbd4b49a699
Revises: d8ecee687b43
Create Date: 2026-02-16 01:30:37.709293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4dbd4b49a699'
down_revision: Union[str, Sequence[str], None] = 'd8ecee687b43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create Enum Type manually
    company_status = sa.Enum('NEW', 'ACTIVE', 'ERROR', 'ARCHIVED', name='companystatus')
    company_status.create(op.get_bind())
    
    # Add Column with default
    op.add_column('companies', sa.Column('status', company_status, nullable=False, server_default='NEW'))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop Column
    op.drop_column('companies', 'status')
    
    # Drop Enum Type
    company_status = sa.Enum('NEW', 'ACTIVE', 'ERROR', 'ARCHIVED', name='companystatus')
    company_status.drop(op.get_bind())
