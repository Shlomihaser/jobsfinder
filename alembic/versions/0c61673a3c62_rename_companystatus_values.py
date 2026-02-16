"""Rename CompanyStatus values

Revision ID: 0c61673a3c62
Revises: d3c89189a483
Create Date: 2026-02-16 01:57:47.797698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c61673a3c62'
down_revision: Union[str, Sequence[str], None] = 'd3c89189a483'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using Temp Column strategy."""
    # 1. Rename old type
    op.execute("ALTER TYPE companystatus RENAME TO companystatus_old")
    
    # 2. Create new type manually
    op.execute("CREATE TYPE companystatus AS ENUM('UNCONFIGURED', 'ACTIVE', 'INACTIVE', 'ERROR')")
    
    # 3. Add new column (nullable first)
    # Note: We must use sa.Enum(... name='companystatus') to refer to the type we just created
    op.add_column('companies', sa.Column('status_new', sa.Enum('UNCONFIGURED', 'ACTIVE', 'INACTIVE', 'ERROR', name='companystatus', create_type=False), nullable=True))
    
    # 4. Copy Data
    op.execute("""
        UPDATE companies SET status_new = CASE
            WHEN status::text = 'NEW' THEN 'UNCONFIGURED'::companystatus
            WHEN status::text = 'ARCHIVED' THEN 'INACTIVE'::companystatus
            ELSE status::text::companystatus
        END
    """)
    
    # 5. Enforce Non-Null if desired (after update)
    op.alter_column('companies', 'status_new', nullable=False, server_default='UNCONFIGURED')

    # 6. Drop old column
    op.drop_column('companies', 'status')
    
    # 7. Rename new column
    op.alter_column('companies', 'status_new', new_column_name='status')
    
    # 8. Drop old type
    op.execute("DROP TYPE companystatus_old")


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse process
    op.execute("ALTER TYPE companystatus RENAME TO companystatus_new")
    op.execute("CREATE TYPE companystatus AS ENUM('NEW', 'ACTIVE', 'ARCHIVED', 'ERROR')")
    
    op.execute("""
        ALTER TABLE companies ALTER COLUMN status TYPE companystatus 
        USING CASE 
            WHEN status::text = 'UNCONFIGURED' THEN 'NEW'::companystatus
            WHEN status::text = 'INACTIVE' THEN 'ARCHIVED'::companystatus
            ELSE status::text::companystatus
        END
    """)
    op.alter_column('companies', 'status', server_default='NEW')
    op.execute("DROP TYPE companystatus_new")
