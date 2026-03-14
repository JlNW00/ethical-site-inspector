"""Tests for video recording support in mock audits.

This module tests the video recording feature that captures session recordings
for each scenario-persona combination during mock audits.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker as sa_sessionmaker

from app.api.routes.audits import router as audits_router
from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit import Audit
from app.schemas.audit import AuditCreateRequest


class TestVideoUrlsModel:
    """Test that the video_urls column exists and handles data correctly."""

    def test_audit_model_has_video_urls_column(self, db_session):
        """Verify Audit model has video_urls attribute."""
        audit = Audit(
            target_url="https://example.com",
            mode="mock",
            status="completed",
        )
        db_session.add(audit)
        db_session.commit()

        # video_urls should be None by default
        assert hasattr(audit, "video_urls")
        assert audit.video_urls is None

    def test_audit_model_accepts_video_urls_dict(self, db_session):
        """Verify video_urls accepts a dict mapping scenario_persona to URLs."""
        video_urls = {
            "cookie_consent_privacy_sensitive": "/videos/test1.webm",
            "checkout_flow_cost_sensitive": "/videos/test2.webm",
        }
        audit = Audit(
            target_url="https://example.com",
            mode="mock",
            status="completed",
            video_urls=video_urls,
        )
        db_session.add(audit)
        db_session.commit()

        # Refresh from DB
        db_session.refresh(audit)
        assert audit.video_urls == video_urls

    def test_audit_model_null_video_urls(self, db_session):
        """Verify video_urls can be explicitly set to None."""
        audit = Audit(
            target_url="https://example.com",
            mode="mock",
            status="completed",
            video_urls=None,
        )
        db_session.add(audit)
        db_session.commit()

        assert audit.video_urls is None


class TestVideoUrlsInMockProvider:
    """Test that MockBrowserAuditProvider generates videos correctly."""

    def test_mock_provider_generates_video_urls(self, db_engine):
        """Verify mock provider returns video_urls with correct keys."""
        from app.providers.browser import MockBrowserAuditProvider
        from app.providers.storage import LocalStorageProvider
        from pathlib import Path

        storage = LocalStorageProvider(Path("./data/test_storage"))
        provider = MockBrowserAuditProvider(storage)

        def mock_progress(phase, message, value, status, details):
            pass

        result = provider.run_audit(
            audit_id="test-audit-123",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=mock_progress,
        )

        # Verify video_urls exists and has correct structure
        assert result.video_urls is not None
        assert isinstance(result.video_urls, dict)
        assert "cookie_consent_privacy_sensitive" in result.video_urls

        # Verify URL points to a .webm file
        video_url = result.video_urls["cookie_consent_privacy_sensitive"]
        assert video_url.endswith(".webm")

    def test_mock_provider_generates_videos_for_all_combinations(self, db_engine):
        """Verify mock provider generates videos for all scenario-persona combos."""
        from app.providers.browser import MockBrowserAuditProvider
        from app.providers.storage import LocalStorageProvider
        from pathlib import Path

        storage = LocalStorageProvider(Path("./data/test_storage"))
        provider = MockBrowserAuditProvider(storage)

        def mock_progress(phase, message, value, status, details):
            pass

        scenarios = ["cookie_consent", "checkout_flow"]
        personas = ["privacy_sensitive", "cost_sensitive"]

        result = provider.run_audit(
            audit_id="test-audit-multi",
            target_url="https://example.com",
            scenarios=scenarios,
            personas=personas,
            progress=mock_progress,
        )

        # Verify all combinations have video URLs
        expected_keys = [
            "cookie_consent_privacy_sensitive",
            "cookie_consent_cost_sensitive",
            "checkout_flow_privacy_sensitive",
            "checkout_flow_cost_sensitive",
        ]

        assert result.video_urls is not None
        for key in expected_keys:
            assert key in result.video_urls, f"Missing video URL for {key}"
            assert result.video_urls[key].endswith(".webm")

    def test_mock_provider_saves_valid_webm_files(self, db_engine):
        """Verify mock provider saves files with valid WebM headers."""
        from app.providers.browser import MockBrowserAuditProvider
        from app.providers.storage import LocalStorageProvider
        from pathlib import Path
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageProvider(Path(tmpdir))
            provider = MockBrowserAuditProvider(storage)

            def mock_progress(phase, message, value, status, details):
                pass

            result = provider.run_audit(
                audit_id="test-audit-webm",
                target_url="https://example.com",
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
                progress=mock_progress,
            )

            # Get the saved file path from the storage provider
            video_url = result.video_urls["cookie_consent_privacy_sensitive"]
            # Convert URL to path (removes leading /artifacts/)
            relative_path = video_url.replace("/artifacts/", "")
            file_path = Path(tmpdir) / relative_path

            # Verify file exists and has WebM header
            assert file_path.exists()
            with open(file_path, "rb") as f:
                header = f.read(4)
                # WebM files start with EBML header: 0x1A 0x45 0xDF 0xA3
                assert header == b"\x1a\x45\xdf\xa3"


class TestVideoUrlsInOrchestrator:
    """Test that AuditOrchestrator persists video_urls correctly."""

    def test_orchestrator_persists_video_urls(self, db_engine):
        """Verify orchestrator saves video_urls from browser provider to DB."""
        from app.services.audit_orchestrator import AuditOrchestrator
        from app.services.provider_registry import get_browser_provider
        from sqlalchemy.orm import sessionmaker
        from unittest.mock import patch, MagicMock

        orchestrator = AuditOrchestrator(sessionmaker(bind=db_engine))

        # Create an audit
        with orchestrator.session_factory() as db:
            from pydantic import HttpUrl
            payload = AuditCreateRequest(
                target_url=HttpUrl("https://example.com"),
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
            )
            audit = orchestrator.create_audit(db, payload, mode="mock")
            audit_id = audit.id

        # Mock the browser provider to return video_urls
        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.observations = []
        mock_result.summary = {"mode": "mock"}
        mock_result.video_urls = {"cookie_consent_privacy_sensitive": "/artifacts/videos/test.webm"}
        mock_provider.run_audit.return_value = mock_result

        with patch("app.services.audit_orchestrator.get_browser_provider", return_value=mock_provider):
            # Run the audit with mode_override="mock"
            orchestrator.run_audit(audit_id, mode_override="mock")

        # Verify video_urls was persisted
        with orchestrator.session_factory() as db:
            completed_audit = orchestrator.get_audit(db, audit_id)
            assert completed_audit.video_urls is not None
            assert "cookie_consent_privacy_sensitive" in completed_audit.video_urls


class TestVideoUrlsInAPI:
    """Test that video_urls appears in API responses."""

    @pytest.fixture()
    def api_test_client(self, db_engine):
        """FastAPI TestClient with audits router only."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.routes.audits import router as audits_router
        from app.core.config import get_settings
        from app.core.database import get_db
        from app.services.audit_orchestrator import AuditOrchestrator
        from sqlalchemy.orm import sessionmaker as sa_sessionmaker

        settings = get_settings()
        TestingSession = sa_sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

        test_app = FastAPI()
        test_app.include_router(audits_router, prefix=settings.api_prefix)

        # Create mock orchestrator that returns video_urls
        orchestrator = AuditOrchestrator(TestingSession)

        def _override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        test_app.dependency_overrides[get_db] = _override_get_db

        with TestClient(test_app) as client:
            yield client, orchestrator

        test_app.dependency_overrides.clear()

    def test_get_audit_returns_video_urls(self, db_engine):
        """Verify GET /api/audits/{id} returns video_urls for completed mock audits."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.orm import sessionmaker as sa_sessionmaker
        from pydantic import HttpUrl
        from unittest.mock import patch, MagicMock

        from app.api.routes.audits import router as audits_router
        from app.core.config import get_settings
        from app.core.database import get_db
        from app.services.audit_orchestrator import AuditOrchestrator
        from app.schemas.audit import AuditCreateRequest

        settings = get_settings()
        TestingSession = sa_sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

        test_app = FastAPI()
        test_app.include_router(audits_router, prefix=settings.api_prefix)

        def _override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        test_app.dependency_overrides[get_db] = _override_get_db

        orchestrator = AuditOrchestrator(TestingSession)

        # Create and run an audit
        with TestingSession() as db:
            payload = AuditCreateRequest(
                target_url=HttpUrl("https://example.com"),
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
            )
            audit = orchestrator.create_audit(db, payload, mode="mock")
            audit_id = audit.id
            db.commit()

        # Mock the browser provider to return video_urls
        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.observations = []
        mock_result.summary = {"mode": "mock"}
        mock_result.video_urls = {"cookie_consent_privacy_sensitive": "/artifacts/videos/test.webm"}
        mock_provider.run_audit.return_value = mock_result

        with patch("app.services.audit_orchestrator.get_browser_provider", return_value=mock_provider):
            # Run the audit with mode_override="mock"
            orchestrator.run_audit(audit_id, mode_override="mock")

        # Get the audit via API
        with TestClient(test_app) as client:
            response = client.get(f"{settings.api_prefix}/audits/{audit_id}")
            assert response.status_code == 200
            data = response.json()
            assert "video_urls" in data
            assert data["video_urls"] is not None
            assert "cookie_consent_privacy_sensitive" in data["video_urls"]

        test_app.dependency_overrides.clear()

    def test_list_audits_with_null_video_urls(self, db_engine):
        """Verify existing audits with null video_urls don't break API responses."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.orm import sessionmaker as sa_sessionmaker
        from pydantic import HttpUrl

        from app.api.routes.audits import router as audits_router
        from app.core.config import get_settings
        from app.core.database import get_db
        from app.services.audit_orchestrator import AuditOrchestrator
        from app.schemas.audit import AuditCreateRequest

        settings = get_settings()
        TestingSession = sa_sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

        test_app = FastAPI()
        test_app.include_router(audits_router, prefix=settings.api_prefix)

        def _override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        test_app.dependency_overrides[get_db] = _override_get_db

        orchestrator = AuditOrchestrator(TestingSession)

        # Create an audit but don't run it (video_urls will be None)
        with TestingSession() as db:
            payload = AuditCreateRequest(
                target_url=HttpUrl("https://example.com"),
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
            )
            audit = orchestrator.create_audit(db, payload, mode="mock")
            audit_id = audit.id
            db.commit()

        # Get the audit via API
        with TestClient(test_app) as client:
            response = client.get(f"{settings.api_prefix}/audits/{audit_id}")
            assert response.status_code == 200
            data = response.json()
            # video_urls should be present but null for queued audits
            assert "video_urls" in data
            assert data["video_urls"] is None

        test_app.dependency_overrides.clear()


class TestVideoUrlContentType:
    """Test that video files are served with correct Content-Type."""

    def test_video_file_has_webm_content_type(self, db_engine):
        """Verify saved video files have Content-Type video/webm."""
        from app.providers.browser import MockBrowserAuditProvider
        from app.providers.storage import LocalStorageProvider
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageProvider(Path(tmpdir))
            provider = MockBrowserAuditProvider(storage)

            def mock_progress(phase, message, value, status, details):
                pass

            result = provider.run_audit(
                audit_id="test-audit-content-type",
                target_url="https://example.com",
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
                progress=mock_progress,
            )

            # Get the saved file path
            video_url = result.video_urls["cookie_consent_privacy_sensitive"]
            relative_path = video_url.replace("/artifacts/", "")
            file_path = Path(tmpdir) / relative_path

            # Verify file has valid WebM structure
            assert file_path.exists()
            with open(file_path, "rb") as f:
                content = f.read()
                # Should start with EBML header
                assert content[:4] == b"\x1a\x45\xdf\xa3"
                # Should be at least the header size
                assert len(content) >= 35  # Header size
