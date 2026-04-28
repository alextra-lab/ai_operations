"""
Unit tests for run manifests router.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.routers.run_manifests import router
from app.schemas.run_manifest import (
    ResultKind,
    RunManifest,
    RunManifestStats,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestRunManifestsRouter:
    """Test cases for run manifests router."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""

        # Override the get_db dependency
        async def mock_get_db():
            yield AsyncMock()

        from app.db.database import get_db

        app.dependency_overrides[get_db] = mock_get_db

        return TestClient(app)

    @pytest.fixture
    def mock_service(self):
        """Create mock run manifest service."""
        with patch("app.routers.run_manifests.RunManifestService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            yield service_instance

    def test_create_run_manifest(self, client, mock_service):
        """Test creating a run manifest."""
        run_id = uuid4()
        now = datetime.utcnow()
        mock_manifest = RunManifest(
            run_id=run_id,
            use_case_id="test-use-case",
            template_ver="1.0",
            model_name="gpt-4",
            model_version="1.0",
            params_hash="abc123",
            schema_valid=True,
            conformance=0.95,
            tool_chain=["search"],
            idempotence_ok=True,
            latency_total_ms=2000,
            latency_llm_ms=1500,
            latency_tools_ms=500,
            tokens_in=100,
            tokens_out=50,
            result_kind=ResultKind.SUCCESS,
            ts_utc=now,
            created_at=now,
            updated_at=now,
        )
        mock_service.create_manifest = AsyncMock(return_value=mock_manifest)

        response = client.post(
            "/api/v1/run-manifests",
            json={
                "use_case_id": "test-use-case",
                "template_ver": "1.0",
                "model_name": "gpt-4",
                "model_version": "1.0",
                "params_hash": "abc123",
                "schema_valid": True,
                "conformance": 0.95,
                "tool_chain": ["search"],
                "idempotence_ok": True,
                "latency_total_ms": 2000,
                "latency_llm_ms": 1500,
                "latency_tools_ms": 500,
                "tokens_in": 100,
                "tokens_out": 50,
                "result_kind": "success",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["use_case_id"] == "test-use-case"
        assert data["result_kind"] == "success"

    def test_get_run_manifest(self, client, mock_service):
        """Test getting a run manifest by ID."""
        run_id = uuid4()
        now = datetime.utcnow()
        mock_manifest = RunManifest(
            run_id=run_id,
            use_case_id="test-use-case",
            template_ver="1.0",
            model_name="gpt-4",
            model_version="1.0",
            params_hash="abc123",
            schema_valid=True,
            conformance=0.95,
            tool_chain=["search"],
            idempotence_ok=True,
            latency_total_ms=2000,
            latency_llm_ms=1500,
            latency_tools_ms=500,
            tokens_in=100,
            tokens_out=50,
            result_kind=ResultKind.SUCCESS,
            ts_utc=now,
            created_at=now,
            updated_at=now,
        )
        mock_service.get_manifest = AsyncMock(return_value=mock_manifest)

        response = client.get(f"/api/v1/run-manifests/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(run_id)
        assert data["use_case_id"] == "test-use-case"

    def test_get_run_manifest_not_found(self, client, mock_service):
        """Test getting non-existent run manifest."""
        run_id = uuid4()
        mock_service.get_manifest = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/run-manifests/{run_id}")
        assert response.status_code == 404

    def test_query_run_manifests(self, client, mock_service):
        """Test querying run manifests."""
        now = datetime.utcnow()
        mock_manifests = [
            RunManifest(
                run_id=uuid4(),
                use_case_id="test-use-case",
                template_ver="1.0",
                model_name="gpt-4",
                model_version="1.0",
                params_hash="abc123",
                schema_valid=True,
                conformance=0.95,
                tool_chain=["search"],
                idempotence_ok=True,
                latency_total_ms=2000,
                latency_llm_ms=1500,
                latency_tools_ms=500,
                tokens_in=100,
                tokens_out=50,
                result_kind=ResultKind.SUCCESS,
                ts_utc=now,
                created_at=now,
                updated_at=now,
            )
        ]
        mock_service.query_manifests = AsyncMock(return_value=mock_manifests)

        response = client.get(
            "/api/v1/run-manifests/",
            params={
                "use_case_id": "test-use-case",
                "result_kind": "success",
                "limit": 10,
                "offset": 0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["use_case_id"] == "test-use-case"

    def test_get_run_manifest_stats(self, client, mock_service):
        """Test getting run manifest statistics."""
        mock_stats = RunManifestStats(
            total_runs=100,
            success_rate=0.95,
            avg_latency_ms=1500.0,
            avg_conformance=0.92,
            total_tokens=12000,
            error_count=5,
            policy_block_count=2,
            contract_violation_count=3,
        )
        mock_service.get_manifest_stats = AsyncMock(return_value=mock_stats)

        response = client.get("/api/v1/run-manifests/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 100
        assert data["success_rate"] == 0.95
