"""add social follower snapshots table

Revision ID: c5d6e7f8a9b0
Revises: b4c3d2e1f0a9
Create Date: 2026-05-13 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b4c3d2e1f0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_follower_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("follower_count", sa.Integer(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "snapshot_date", name="uq_social_follower_snapshot_user_day"),
    )
    op.create_index(
        "idx_social_follower_snapshot_user_date",
        "social_follower_snapshots",
        ["user_id", "snapshot_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_social_follower_snapshots_user_id"),
        "social_follower_snapshots",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_social_follower_snapshots_user_id"), table_name="social_follower_snapshots")
    op.drop_index("idx_social_follower_snapshot_user_date", table_name="social_follower_snapshots")
    op.drop_table("social_follower_snapshots")
