"""add hot_topic fetch_batch and thumbnail_url

Revision ID: a3b2c1d4e5f6
Revises: 21cd16f14553
Create Date: 2026-05-12 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a3b2c1d4e5f6'
down_revision: Union[str, None] = '21cd16f14553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hot_topics', sa.Column('thumbnail_url', sa.String(), server_default='', nullable=True))
    op.add_column('hot_topics', sa.Column('fetch_batch', sa.String(), server_default='', nullable=False))
    op.create_index('idx_hot_topic_fetch_batch', 'hot_topics', ['fetch_batch'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_hot_topic_fetch_batch', table_name='hot_topics')
    op.drop_column('hot_topics', 'fetch_batch')
    op.drop_column('hot_topics', 'thumbnail_url')
