import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base


class IdeaCard(Base):
    __tablename__ = "idea_cards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String), default=list)
    hot_topic_id = Column(String, ForeignKey("hot_topics.id"), nullable=True)
    chat_session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="idea_cards")
    hot_topic = relationship("HotTopic")
    chat_session = relationship("ChatSession")
