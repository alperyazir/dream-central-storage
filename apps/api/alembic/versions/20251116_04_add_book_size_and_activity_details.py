"""add book size and activity details

Revision ID: 20251116_04
Revises: 20251116_03
Create Date: 2025-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251116_04'
down_revision: Union[str, None] = '20251116_03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('total_size', sa.BigInteger(), nullable=True))
    op.add_column('books', sa.Column('activity_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'activity_details')
    op.drop_column('books', 'total_size')
