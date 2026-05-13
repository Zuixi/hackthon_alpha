import uuid
from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class SocialFollowerSnapshot(Base):
    __tablename__ = "social_follower_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    follower_count = Column(Integer, nullable=False, default=0)
    refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_social_follower_snapshot_user_day"),
        Index("idx_social_follower_snapshot_user_date", "user_id", "snapshot_date"),
    )
