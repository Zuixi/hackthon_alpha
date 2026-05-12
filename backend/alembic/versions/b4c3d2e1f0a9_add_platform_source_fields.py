"""add platform and source fields to hot_topics

Revision ID: b4c3d2e1f0a9
Revises: a3b2c1d4e5f6
Create Date: 2026-05-13 01:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b4c3d2e1f0a9'
down_revision: Union[str, None] = 'a3b2c1d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hot_topics', sa.Column('platform', sa.String(), server_default='zhihu', nullable=False))
    op.add_column('hot_topics', sa.Column('source', sa.String(), server_default='zhihu_api', nullable=False))
    op.create_index('idx_hot_topic_platform', 'hot_topics', ['platform'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_hot_topic_platform', table_name='hot_topics')
    op.drop_column('hot_topics', 'source')
    op.drop_column('hot_topics', 'platform')
