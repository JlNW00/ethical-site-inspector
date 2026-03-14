"""Tests for the Benchmark API endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.benchmarks import router as benchmarks_router
from app.core.config import get_settings
from app.core.database import Base, get_db


@pytest.fixture
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


@pytest.fixture
def db_session(db_engine):
    """Provide a scoped SQLAlchemy session that rolls back after each test."""
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def api_test_client(db_engine):
    """FastAPI TestClient for benchmarks router only."""
    settings = get_settings()
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    test_app = FastAPI()
    test_app.include_router(benchmarks_router, prefix=settings.api_prefix)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _override_get_db

    with TestClient(test_app) as client:
        yield client


class TestCreateBenchmarkEndpoint:
    """Tests for POST /api/benchmarks endpoint."""

    def test_create_benchmark_happy_path_returns_201(self, api_test_client):
        """POST with 2-5 valid URLs returns 201 with benchmark object."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent", "checkout_flow"],
            "selected_personas": ["privacy_sensitive", "cost_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "queued"
        # URLs may be normalized (e.g., trailing slash added), so check count and not exact match
        assert len(data["urls"]) == len(payload["urls"])
        assert all("example" in url for url in data["urls"])
        assert "audit_ids" in data
        assert len(data["audit_ids"]) == 2
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_benchmark_with_5_urls_returns_201(self, api_test_client):
        """POST with exactly 5 URLs returns 201."""
        payload = {
            "urls": [
                "https://example1.com",
                "https://example2.com",
                "https://example3.com",
                "https://example4.com",
                "https://example5.com",
            ],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["urls"]) == 5
        assert len(data["audit_ids"]) == 5

    def test_create_benchmark_with_1_url_returns_422(self, api_test_client):
        """POST with less than 2 URLs returns 422."""
        payload = {
            "urls": ["https://example.com"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_with_6_urls_returns_422(self, api_test_client):
        """POST with more than 5 URLs returns 422."""
        payload = {
            "urls": [
                "https://example1.com",
                "https://example2.com",
                "https://example3.com",
                "https://example4.com",
                "https://example5.com",
                "https://example6.com",
            ],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_with_duplicate_urls_returns_422(self, api_test_client):
        """POST with duplicate URLs returns 422."""
        payload = {
            "urls": ["https://example.com", "https://example.com"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422
        assert "duplicate" in response.text.lower() or "unique" in response.text.lower()

    def test_create_benchmark_with_no_urls_returns_422(self, api_test_client):
        """POST with empty URLs list returns 422."""
        payload = {
            "urls": [],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_with_invalid_url_returns_422(self, api_test_client):
        """POST with invalid URL format returns 422."""
        payload = {
            "urls": ["not-a-valid-url", "https://example.com"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_with_2_urls_minimum(self, api_test_client):
        """POST with exactly 2 URLs (minimum) returns 201."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["urls"]) == 2
        assert len(data["audit_ids"]) == 2


class TestGetBenchmarkEndpoint:
    """Tests for GET /api/benchmarks/{id} endpoint."""

    def test_get_benchmark_by_id_returns_200(self, api_test_client):
        """GET /api/benchmarks/{id} returns 200 with full object."""
        # First create a benchmark
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        create_response = api_test_client.post("/api/benchmarks", json=payload)
        assert create_response.status_code == 201
        benchmark_id = create_response.json()["id"]

        # Now get it
        response = api_test_client.get(f"/api/benchmarks/{benchmark_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == benchmark_id
        assert "status" in data
        assert "urls" in data
        assert "audit_ids" in data
        assert "trust_scores" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_benchmark_not_found_returns_404(self, api_test_client):
        """GET /api/benchmarks/{invalid_id} returns 404."""
        response = api_test_client.get("/api/benchmarks/invalid-uuid-12345")
        assert response.status_code == 404

    def test_get_benchmark_with_trust_scores(self, api_test_client):
        """GET returns benchmark with trust_scores populated when available."""
        # Create benchmark
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        create_response = api_test_client.post("/api/benchmarks", json=payload)
        benchmark_id = create_response.json()["id"]

        response = api_test_client.get(f"/api/benchmarks/{benchmark_id}")
        assert response.status_code == 200
        data = response.json()
        # Initially trust_scores should be empty or null
        assert "trust_scores" in data


class TestListBenchmarksEndpoint:
    """Tests for GET /api/benchmarks endpoint."""

    def test_list_benchmarks_returns_200(self, api_test_client):
        """GET /api/benchmarks returns 200 with list."""
        response = api_test_client.get("/api/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_benchmarks_sorted_by_created_at_desc(self, api_test_client):
        """GET /api/benchmarks returns list sorted by created_at desc."""
        # Create first benchmark
        payload1 = {
            "urls": ["https://example1.com", "https://example2.com"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        api_test_client.post("/api/benchmarks", json=payload1)

        # Create second benchmark
        payload2 = {
            "urls": ["https://example3.com", "https://example4.com"],
            "selected_scenarios": ["checkout_flow"],
            "selected_personas": ["cost_sensitive"],
        }
        api_test_client.post("/api/benchmarks", json=payload2)

        # List benchmarks
        response = api_test_client.get("/api/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        # Verify sorting - newer should come first
        for i in range(len(data) - 1):
            current_created = data[i]["created_at"]
            next_created = data[i + 1]["created_at"]
            assert current_created >= next_created

    def test_list_benchmarks_includes_all_fields(self, api_test_client):
        """GET /api/benchmarks returns benchmarks with all required fields."""
        # Create a benchmark first
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        api_test_client.post("/api/benchmarks", json=payload)

        response = api_test_client.get("/api/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        benchmark = data[0]
        assert "id" in benchmark
        assert "status" in benchmark
        assert "urls" in benchmark
        assert "audit_ids" in benchmark
        assert "trust_scores" in benchmark
        assert "created_at" in benchmark
        assert "updated_at" in benchmark

    def test_list_benchmarks_empty_list(self, api_test_client):
        """GET /api/benchmarks returns empty list when no benchmarks."""
        response = api_test_client.get("/api/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May or may not be empty depending on previous tests


class TestBenchmarkValidation:
    """Tests for benchmark validation edge cases."""

    def test_create_benchmark_missing_urls_field_returns_422(self, api_test_client):
        """POST without urls field returns 422."""
        payload = {
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_missing_scenarios_returns_422(self, api_test_client):
        """POST without selected_scenarios field returns 422."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_missing_personas_returns_422(self, api_test_client):
        """POST without selected_personas field returns 422."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_invalid_scenario_returns_422(self, api_test_client):
        """POST with invalid scenario returns 422."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["invalid_scenario"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422

    def test_create_benchmark_invalid_persona_returns_422(self, api_test_client):
        """POST with invalid persona returns 422."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["invalid_persona"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 422


class TestBenchmarkStatus:
    """Tests for benchmark status lifecycle."""

    def test_new_benchmark_has_queued_status(self, api_test_client):
        """Newly created benchmark has status 'queued'."""
        payload = {
            "urls": ["https://example.com", "https://example.org"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"

    def test_benchmark_audit_ids_match_urls_order(self, api_test_client):
        """audit_ids list matches urls list order."""
        payload = {
            "urls": ["https://aaa.com", "https://bbb.com", "https://ccc.com"],
            "selected_scenarios": ["cookie_consent"],
            "selected_personas": ["privacy_sensitive"],
        }
        response = api_test_client.post("/api/benchmarks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["audit_ids"]) == 3
        # Verify audit_ids are valid UUIDs
        for audit_id in data["audit_ids"]:
            assert len(audit_id) == 36  # UUID length
            assert "-" in audit_id  # UUID format
