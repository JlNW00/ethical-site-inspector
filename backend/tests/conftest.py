"""Shared fixtures for backend unit tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Override DATABASE_URL *before* any app module touches get_settings / engine
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.database import Base


@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide a scoped SQLAlchemy session that rolls back after each test."""
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session: Session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def test_client(db_engine):
    """FastAPI TestClient backed by the in-memory test database.

    Builds a *lightweight* app containing only the health and audits routers
    (no seed-demo lifespan) so the test DB is the sole data source.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    from app.api.routes.health import router as health_router
    from app.core.config import get_settings
    from app.core.database import get_db

    settings = get_settings()
    TestingSession = sa_sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    test_app = FastAPI()
    test_app.include_router(health_router, prefix=settings.api_prefix)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _override_get_db

    # Monkey-patch SessionLocal in health module so the readiness endpoint
    # hits the in-memory DB instead of the production engine.
    import app.api.routes.health as health_mod

    original_session_local = health_mod.SessionLocal
    health_mod.SessionLocal = TestingSession
    try:
        with TestClient(test_app) as client:
            yield client
    finally:
        health_mod.SessionLocal = original_session_local
        test_app.dependency_overrides.clear()
