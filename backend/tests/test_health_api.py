"""Tests for health and readiness API endpoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client):
        resp = test_client.get("/api/health")
        assert resp.status_code == 200

    def test_health_status_ok(self, test_client):
        data = test_client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_health_has_timestamp(self, test_client):
        data = test_client.get("/api/health").json()
        assert "timestamp" in data

    def test_health_has_version(self, test_client):
        data = test_client.get("/api/health").json()
        assert data["version"] == "0.1.0"


class TestReadinessEndpoint:
    def test_readiness_returns_200(self, test_client):
        resp = test_client.get("/api/readiness")
        assert resp.status_code == 200

    def test_readiness_has_expected_fields(self, test_client):
        data = test_client.get("/api/readiness").json()
        expected_fields = {
            "status",
            "configured_mode",
            "effective_mode",
            "browser_provider",
            "classifier_provider",
            "storage_provider",
            "nova_ready",
            "playwright_ready",
            "storage_ready",
            "seeded_demo_audit_id",
        }
        assert expected_fields.issubset(set(data.keys()))

    def test_readiness_status_is_ready(self, test_client):
        data = test_client.get("/api/readiness").json()
        assert data["status"] == "ready"
