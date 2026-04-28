"""Unit tests for admin gateway metrics proxy router."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.routers.admin_gateway_metrics import (
    GatewayMetrics,
    ModelMetrics,
    ProviderMetrics,
    TimeSeriesData,
    get_forward_headers,
    proxy_to_gateway,
    require_admin,
)
from fastapi import HTTPException

from shared.auth.models import TokenPayload


@pytest.fixture
def mock_admin_token():
    """Create a mock admin token payload."""
    return TokenPayload(
        sub="admin-user",
        user_id="00000000-0000-0000-0000-000000000001",
        role="admin",
        exp=9999999999,
        iat=1234567890,
        iss="aio-test",
        token_type="access",
    )


@pytest.fixture
def mock_analyst_token():
    """Create a mock analyst token payload."""
    return TokenPayload(
        sub="analyst-user",
        user_id="00000000-0000-0000-0000-000000000002",
        role="analyst",
        exp=9999999999,
        iat=1234567890,
        iss="aio-test",
        token_type="access",
    )


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock()
    request.headers = {"authorization": "Bearer test-token"}
    return request


class TestRequireAdmin:
    """Test suite for require_admin function."""

    def test_require_admin_allows_admin_role(self, mock_admin_token):
        """Test that admin role is allowed."""
        # Should not raise any exception
        require_admin(mock_admin_token)

    def test_require_admin_blocks_non_admin_role(self, mock_analyst_token):
        """Test that non-admin role is blocked."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin(mock_analyst_token)
        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in str(exc_info.value.detail)


class TestGetForwardHeaders:
    """Test suite for get_forward_headers function."""

    def test_extracts_authorization_header(self, mock_request):
        """Test that authorization header is extracted."""
        headers = get_forward_headers(mock_request)
        assert headers == {"Authorization": "Bearer test-token"}

    def test_handles_missing_authorization(self):
        """Test handling when authorization header is missing."""
        request = MagicMock()
        request.headers = {}
        headers = get_forward_headers(request)
        assert headers == {}


@pytest.mark.asyncio
class TestProxyToGateway:
    """Test suite for proxy_to_gateway function."""

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("httpx.AsyncClient")
    async def test_successful_proxy_request(
        self, mock_client_class, mock_admin_token, mock_request
    ):
        """Test successful proxy request to gateway."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_requests": 100}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await proxy_to_gateway(
            method="GET",
            endpoint="/admin/metrics/aggregate",
            request=mock_request,
            params={"hours": 24},
            current_user=mock_admin_token,
        )

        assert result == {"total_requests": 100}
        mock_client.request.assert_called_once()

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("httpx.AsyncClient")
    async def test_proxy_handles_http_error(
        self, mock_client_class, mock_admin_token, mock_request
    ):
        """Test proxy handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"detail": "Gateway error"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(
            side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_gateway(
                method="GET",
                endpoint="/admin/metrics/aggregate",
                request=mock_request,
                current_user=mock_admin_token,
            )
        assert exc_info.value.status_code == 500

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("httpx.AsyncClient")
    async def test_proxy_handles_timeout(self, mock_client_class, mock_admin_token, mock_request):
        """Test proxy handling of timeout errors."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_gateway(
                method="GET",
                endpoint="/admin/metrics/aggregate",
                request=mock_request,
                current_user=mock_admin_token,
            )
        assert exc_info.value.status_code == 504

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("httpx.AsyncClient")
    async def test_proxy_handles_request_error(
        self, mock_client_class, mock_admin_token, mock_request
    ):
        """Test proxy handling of general request errors."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_gateway(
                method="GET",
                endpoint="/admin/metrics/aggregate",
                request=mock_request,
                current_user=mock_admin_token,
            )
        assert exc_info.value.status_code == 503

    async def test_proxy_blocks_non_admin(self, mock_analyst_token, mock_request):
        """Test that proxy blocks non-admin users."""
        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_gateway(
                method="GET",
                endpoint="/admin/metrics/aggregate",
                request=mock_request,
                current_user=mock_analyst_token,
            )
        assert exc_info.value.status_code == 403


class TestPydanticModels:
    """Test suite for Pydantic models."""

    def test_gateway_metrics_model(self):
        """Test GatewayMetrics model validation."""
        data = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "success_rate": 95.0,
            "total_input_tokens": 5000,
            "total_output_tokens": 3000,
            "total_cost_eur": 0.5,
            "avg_latency_ms": 250.5,
            "p50_latency_ms": 200.0,
            "p95_latency_ms": 400.0,
            "p99_latency_ms": 500.0,
            "unique_models": 3,
            "unique_users": 10,
            "streaming_requests": 20,
        }
        metrics = GatewayMetrics(**data)
        assert metrics.total_requests == 100
        assert metrics.success_rate == 95.0
        assert metrics.total_input_tokens == 5000
        assert metrics.total_output_tokens == 3000

    def test_time_series_data_model(self):
        """Test TimeSeriesData model validation."""
        data = {
            "latency": [{"timestamp": "2025-11-06T12:00:00Z", "value": 250.0}],
            "tokens": [{"timestamp": "2025-11-06T12:00:00Z", "value": 100.0}],
            "cost": [{"timestamp": "2025-11-06T12:00:00Z", "value": 0.01}],
            "requests": [{"timestamp": "2025-11-06T12:00:00Z", "value": 10.0}],
        }
        ts_data = TimeSeriesData(**data)
        assert len(ts_data.latency) == 1
        assert ts_data.latency[0].timestamp == "2025-11-06T12:00:00Z"

    def test_provider_metrics_model(self):
        """Test ProviderMetrics model validation."""
        data = {
            "provider_name": "OpenAI",
            "total_requests": 50,
            "total_cost_eur": 0.3,
            "avg_latency_ms": 230.0,
            "total_input_tokens": 2500,
            "total_output_tokens": 1500,
        }
        provider = ProviderMetrics(**data)
        assert provider.provider_name == "OpenAI"
        assert provider.total_requests == 50
        assert provider.total_input_tokens == 2500
        assert provider.total_output_tokens == 1500

    def test_model_metrics_model(self):
        """Test ModelMetrics model validation."""
        data = {
            "model_name": "gpt-4",
            "total_requests": 30,
            "total_input_tokens": 1500,
            "total_output_tokens": 1000,
            "total_cost_eur": 0.2,
            "avg_latency_ms": 280.0,
        }
        model = ModelMetrics(**data)
        assert model.model_name == "gpt-4"
        assert model.total_requests == 30
        assert model.total_input_tokens == 1500
        assert model.total_output_tokens == 1000
