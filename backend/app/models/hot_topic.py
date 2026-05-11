import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class HotTopic(Base):
    __tablename__ = "hot_topics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String, index=True)
    title = Column(String, nullable=False)
    url = Column(String, default="")
    excerpt = Column(Text, default="")
    hot_score = Column(Integer, default=0)
    answer_count = Column(Integer, default=0)
    follower_count = Column(Integer, default=0)
    detail = Column(Text, default="")
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_hot_topic_fetched", "fetched_at"),
        Index("idx_hot_topic_score", "hot_score"),
    )
