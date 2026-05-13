"""Shared fixtures for tests.

Uses SQLite in-memory for DB-backed tests and overrides FastAPI
dependencies so no real PostgreSQL is needed.
"""

import os
import pytest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MINIMAX_API_KEY", "test-key")
os.environ.setdefault("BYPASS_OAUTH_LOGIN", "true")
os.environ.setdefault("ZHIHU_DEV_API_KEY", "test")
os.environ.setdefault("ZHIHU_APP_ID", "0")
os.environ.setdefault("ZHIHU_APP_KEY", "test")
os.environ.setdefault("ZHIHU_COMMUNITY_APP_KEY", "test")
os.environ.setdefault("ZHIHU_COMMUNITY_APP_SECRET", "test")
os.environ.setdefault("SKILL_AUTO_EXTRACT", "false")

import json
from sqlalchemy import create_engine, event, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

# SQLite doesn't support ARRAY, so we patch IdeaCard.tags column type
class JSONEncodedList(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return "[]"

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return []

# Patch the IdeaCard model before metadata is created
from app.models.idea_card import IdeaCard
IdeaCard.__table__.c.tags.type = JSONEncodedList()

from app.database import Base, get_db
from app.main import app
from app.auth import get_current_user
from app.models.user import User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def test_user(db):
    user = User(zhihu_id="test-zhihu-id", name="TestUser", avatar="", zhihu_token="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def client(db, test_user):
    """TestClient with DB + auth overrides."""
    from fastapi.testclient import TestClient

    def _override_db():
        try:
            yield db
        finally:
            pass

    def _override_user():
        return test_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
