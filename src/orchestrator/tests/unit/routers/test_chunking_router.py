"""
Unit tests for Chunking Proxy Router.

Tests chunking and preflight analysis endpoints that proxy to retrieval service.
P5-A12: Comprehensive async tests (Nov 2025).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.routers.chunking import get_current_user, router
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Create FastAPI app with chunking router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def fake_user():
    """Mock authenticated user."""
    return {"sub": "testuser", "id": "user123"}


@pytest.fixture(autouse=True)
def override_get_current_user(app, fake_user):
    """Override authentication for tests."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides = {}


def create_mock_httpx(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    """Helper to create mock httpx client."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text
    if json_data is not None:
        mock_response.json = MagicMock(return_value=json_data)
    return mock_instance, mock_response


# ============================================================================
# Tests: Router Structure
# ============================================================================


class TestChunkingRouterStructure:
    """Tests for chunking router structure and imports."""

    def test_chunking_router_imports(self):
        """Test that chunking router module imports successfully."""
        from app.routers import chunking

        assert chunking.router is not None
        assert chunking.router.prefix == "/api/v1/chunking"

    def test_router_has_required_endpoints(self):
        """Test that router has all required endpoints."""
        from app.routers import chunking

        routes = [route.path for route in chunking.router.routes]

        expected_endpoints = [
            "/preflight/analyze",
            "/preflight",
            "/compare",
            "/apply",
            "/strategies",
            "/strategies/{strategy}/config",
            "/presets",
            "/presets/{preset_id}",
        ]

        for endpoint in expected_endpoints:
            assert any(endpoint in route for route in routes), f"Missing endpoint: {endpoint}"

    def test_all_endpoints_are_async(self):
        """Verify all endpoint functions are async."""
        import inspect

        from app.routers import chunking

        async_funcs = [
            chunking.preflight_analysis_file,
            chunking.preflight_analysis,
            chunking.compare_strategies,
            chunking.apply_chunking_config,
            chunking.get_available_strategies,
            chunking.get_strategy_config,
            chunking.save_preset,
            chunking.get_presets,
            chunking.delete_preset,
        ]

        for func in async_funcs:
            assert inspect.iscoroutinefunction(func), f"{func.__name__} is not async"


# ============================================================================
# Tests: Preflight Analysis with File Upload
# ============================================================================


class TestPreflightAnalysisFile:
    """Tests for preflight analysis with file upload endpoint."""

    @pytest.mark.asyncio
    def test_preflight_analysis_txt_file_success(self, client):
        """Test preflight analysis with text file."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "recommended_strategy": "semantic",
                "analysis": {"chunk_count": 10, "avg_chunk_size": 500},
            },
        )
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            files = {"file": ("test.txt", b"This is test content", "text/plain")}
            data = {"collection_name": "default"}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["recommended_strategy"] == "semantic"

    @pytest.mark.asyncio
    def test_preflight_analysis_md_file_success(self, client):
        """Test preflight analysis with markdown file."""
        mock_instance, mock_response = create_mock_httpx(200, {"recommended_strategy": "markdown"})
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            files = {"file": ("readme.md", b"# Header\n\nContent here", "text/markdown")}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files)
            assert response.status_code == 200

    @pytest.mark.asyncio
    def test_preflight_analysis_pdf_file_success(self, client):
        """Test preflight analysis with PDF file (mocked extraction)."""
        mock_instance, mock_response = create_mock_httpx(200, {"recommended_strategy": "page"})
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with (
            patch("httpx.AsyncClient", return_value=mock_instance),
            patch("pdfplumber.open", return_value=mock_pdf),
        ):
            # Create a minimal PDF-like file
            files = {"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files)
            assert response.status_code == 200

    @pytest.mark.asyncio
    def test_preflight_analysis_unsupported_file_type(self, client):
        """Test preflight analysis with unsupported file type."""
        files = {"file": ("test.xlsx", b"excel data", "application/vnd.ms-excel")}
        response = client.post("/api/v1/chunking/preflight/analyze", files=files)
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    def test_preflight_analysis_docx_not_supported(self, client):
        """Test preflight analysis rejects DOCX files."""
        files = {"file": ("test.docx", b"docx data", "application/docx")}
        response = client.post("/api/v1/chunking/preflight/analyze", files=files)
        assert response.status_code == 400
        assert "DOCX" in response.json()["detail"]

    @pytest.mark.asyncio
    def test_preflight_analysis_with_strategies(self, client):
        """Test preflight analysis with custom strategies."""
        mock_instance, mock_response = create_mock_httpx(
            200, {"strategies_compared": ["semantic", "fixed"]}
        )
        mock_post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__.return_value.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_instance):
            files = {"file": ("test.txt", b"content", "text/plain")}
            data = {"strategies": '["semantic", "fixed"]'}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files, data=data)
            assert response.status_code == 200

    @pytest.mark.asyncio
    def test_preflight_analysis_with_test_suite_id(self, client):
        """Test preflight analysis with test suite ID."""
        mock_instance, mock_response = create_mock_httpx(200, {"analysis": "ok"})
        mock_post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__.return_value.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_instance):
            files = {"file": ("test.txt", b"content", "text/plain")}
            data = {"test_suite_id": "suite-123"}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files, data=data)
            assert response.status_code == 200
            # Verify test_suite_id was passed to corpus service
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["test_suite_id"] == "suite-123"

    @pytest.mark.asyncio
    def test_preflight_analysis_error(self, client):
        """Test preflight analysis error handling."""
        mock_instance, mock_response = create_mock_httpx(500, text="Server error")
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            files = {"file": ("test.txt", b"content", "text/plain")}
            response = client.post("/api/v1/chunking/preflight/analyze", files=files)
            assert response.status_code == 500


# ============================================================================
# Tests: Preflight Analysis (JSON)
# ============================================================================


class TestPreflightAnalysisJSON:
    """Tests for preflight analysis with JSON payload."""

    @pytest.mark.asyncio
    def test_preflight_analysis_json_success(self, client):
        """Test preflight analysis with JSON text payload."""
        mock_instance, mock_response = create_mock_httpx(
            200, {"recommended_strategy": "semantic", "chunk_analysis": {}}
        )
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            payload = {
                "text": "This is the document text to analyze",
                "document_name": "test.txt",
                "document_type": "text/plain",
            }
            response = client.post("/api/v1/chunking/preflight", json=payload)
            assert response.status_code == 200
            assert response.json()["recommended_strategy"] == "semantic"

    @pytest.mark.asyncio
    def test_preflight_analysis_json_error(self, client):
        """Test preflight analysis JSON error handling."""
        mock_instance, mock_response = create_mock_httpx(400, text="Invalid payload")
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.post("/api/v1/chunking/preflight", json={"text": ""})
            assert response.status_code == 400


# ============================================================================
# Tests: Compare Strategies
# ============================================================================


class TestCompareStrategies:
    """Tests for strategy comparison endpoint."""

    @pytest.mark.asyncio
    def test_compare_strategies_success(self, client):
        """Test comparing multiple chunking strategies."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "comparison": [
                    {"strategy": "semantic", "score": 0.9},
                    {"strategy": "fixed", "score": 0.7},
                ]
            },
        )
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            payload = {
                "text": "Document text",
                "strategies": ["semantic", "fixed"],
            }
            response = client.post("/api/v1/chunking/compare", json=payload)
            assert response.status_code == 200
            assert len(response.json()["comparison"]) == 2

    @pytest.mark.asyncio
    def test_compare_strategies_error(self, client):
        """Test compare strategies error handling."""
        mock_instance, mock_response = create_mock_httpx(422, text="Invalid strategies")
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.post("/api/v1/chunking/compare", json={"strategies": []})
            assert response.status_code == 422


# ============================================================================
# Tests: Apply Chunking Config
# ============================================================================


class TestApplyChunkingConfig:
    """Tests for applying chunking configuration."""

    @pytest.mark.asyncio
    def test_apply_chunking_config_success(self, client):
        """Test applying chunking configuration to document."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "chunks": [{"text": "chunk1"}, {"text": "chunk2"}],
                "total_chunks": 2,
            },
        )
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            payload = {
                "document_id": "doc-123",
                "strategy": "semantic",
                "chunk_size": 500,
            }
            response = client.post("/api/v1/chunking/apply", json=payload)
            assert response.status_code == 200
            assert response.json()["total_chunks"] == 2

    @pytest.mark.asyncio
    def test_apply_chunking_config_error(self, client):
        """Test apply chunking error handling."""
        mock_instance, mock_response = create_mock_httpx(404, text="Document not found")
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.post("/api/v1/chunking/apply", json={"document_id": "invalid"})
            assert response.status_code == 404


# ============================================================================
# Tests: Get Available Strategies
# ============================================================================


class TestGetStrategies:
    """Tests for getting available chunking strategies."""

    @pytest.mark.asyncio
    def test_get_strategies_success(self, client):
        """Test retrieving available strategies."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "strategies": [
                    {"name": "semantic", "description": "Semantic chunking"},
                    {"name": "fixed", "description": "Fixed size chunks"},
                ]
            },
        )
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/strategies")
            assert response.status_code == 200
            assert "strategies" in response.json()

    @pytest.mark.asyncio
    def test_get_strategies_error(self, client):
        """Test get strategies error handling."""
        mock_instance, mock_response = create_mock_httpx(500, text="Server error")
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/strategies")
            assert response.status_code == 500


# ============================================================================
# Tests: Get Strategy Config
# ============================================================================


class TestGetStrategyConfig:
    """Tests for getting specific strategy configuration."""

    @pytest.mark.asyncio
    def test_get_strategy_config_success(self, client):
        """Test retrieving specific strategy configuration."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "strategy": "semantic",
                "config": {
                    "chunk_size": 500,
                    "overlap": 50,
                    "min_chunk_size": 100,
                },
            },
        )
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/strategies/semantic/config")
            assert response.status_code == 200
            assert response.json()["strategy"] == "semantic"

    @pytest.mark.asyncio
    def test_get_strategy_config_not_found(self, client):
        """Test get config for non-existent strategy."""
        mock_instance, mock_response = create_mock_httpx(404, text="Strategy not found")
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/strategies/invalid_strategy/config")
            assert response.status_code == 404


# ============================================================================
# Tests: Presets Management
# ============================================================================


class TestPresetsManagement:
    """Tests for chunking presets CRUD operations."""

    @pytest.mark.asyncio
    def test_save_preset_success(self, client):
        """Test saving a chunking preset."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "id": "preset-123",
                "name": "My Preset",
                "strategy": "semantic",
            },
        )
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            payload = {
                "name": "My Preset",
                "strategy": "semantic",
                "config": {"chunk_size": 500},
            }
            response = client.post("/api/v1/chunking/presets", json=payload)
            assert response.status_code == 200
            assert response.json()["name"] == "My Preset"

    @pytest.mark.asyncio
    def test_save_preset_error(self, client):
        """Test save preset error handling."""
        mock_instance, mock_response = create_mock_httpx(400, text="Invalid preset")
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.post("/api/v1/chunking/presets", json={})
            assert response.status_code == 400

    @pytest.mark.asyncio
    def test_get_presets_success(self, client):
        """Test retrieving all presets."""
        mock_instance, mock_response = create_mock_httpx(
            200,
            {
                "presets": [
                    {"id": "p1", "name": "Preset 1"},
                    {"id": "p2", "name": "Preset 2"},
                ]
            },
        )
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/presets")
            assert response.status_code == 200
            assert len(response.json()["presets"]) == 2

    @pytest.mark.asyncio
    def test_get_presets_error(self, client):
        """Test get presets error handling."""
        mock_instance, mock_response = create_mock_httpx(500, text="Server error")
        mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.get("/api/v1/chunking/presets")
            assert response.status_code == 500

    @pytest.mark.asyncio
    def test_delete_preset_success(self, client):
        """Test deleting a preset."""
        mock_instance, mock_response = create_mock_httpx(200, {"deleted": True, "id": "preset-123"})
        mock_instance.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.delete("/api/v1/chunking/presets/preset-123")
            assert response.status_code == 200
            assert response.json()["deleted"] is True

    @pytest.mark.asyncio
    def test_delete_preset_not_found(self, client):
        """Test delete non-existent preset."""
        mock_instance, mock_response = create_mock_httpx(404, text="Preset not found")
        mock_instance.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            response = client.delete("/api/v1/chunking/presets/invalid-id")
            assert response.status_code == 404


# ============================================================================
# Tests: Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Tests for chunking router helper functions."""

    def test_get_forward_headers_with_auth(self):
        """Test get_forward_headers extracts authorization."""
        from typing import ClassVar

        from app.routers import chunking

        class MockRequest:
            headers: ClassVar[dict[str, str]] = {"authorization": "Bearer token123"}

        result = chunking.get_forward_headers(MockRequest())
        assert result == {"authorization": "Bearer token123"}

    def test_get_forward_headers_without_auth(self):
        """Test get_forward_headers handles missing auth."""
        from typing import ClassVar

        from app.routers import chunking

        class MockRequest:
            headers: ClassVar[dict[str, str]] = {}

        result = chunking.get_forward_headers(MockRequest())
        assert result == {}

    def test_get_forward_headers_other_headers_ignored(self):
        """Test get_forward_headers only forwards authorization."""
        from typing import ClassVar

        from app.routers import chunking

        class MockRequest:
            headers: ClassVar[dict[str, str]] = {
                "authorization": "Bearer token",
                "content-type": "application/json",
                "x-custom": "value",
            }

        result = chunking.get_forward_headers(MockRequest())
        assert result == {"authorization": "Bearer token"}
        assert "content-type" not in result
        assert "x-custom" not in result
