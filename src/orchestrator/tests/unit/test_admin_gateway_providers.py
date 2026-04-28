"""Unit tests for admin gateway providers proxy router."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from app.routers.admin_gateway_providers import (
    delete_provider,
    get_forward_headers,
    proxy_to_gateway,
    require_admin,
    update_provider,
)
from fastapi import HTTPException, Request

from shared.auth.models import TokenPayload
from shared.providers import ProviderConfig, ProviderConfigUpdate


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
    request = MagicMock(spec=Request)
    request.headers = {"authorization": "Bearer test-token"}
    return request


class TestGetForwardHeaders:
    """Test get_forward_headers function."""

    def test_extracts_authorization_header(self, mock_request):
        """Test that authorization header is extracted."""
        headers = get_forward_headers(mock_request)
        assert headers == {"Authorization": "Bearer test-token"}

    def test_handles_missing_authorization(self):
        """Test that missing authorization header is handled."""
        request = MagicMock(spec=Request)
        request.headers = {}
        headers = get_forward_headers(request)
        assert headers == {}


class TestRequireAdmin:
    """Test require_admin function."""

    def test_allows_admin(self, mock_admin_token):
        """Test that admin users are allowed."""
        # Should not raise
        require_admin(mock_admin_token)

    def test_blocks_non_admin(self, mock_analyst_token):
        """Test that non-admin users are blocked."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin(mock_analyst_token)
        assert exc_info.value.status_code == 403


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
        mock_response.json.return_value = {"id": "123", "name": "test-provider"}
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await proxy_to_gateway(
            method="GET",
            endpoint="/admin/providers",
            request=mock_request,
            current_user=mock_admin_token,
        )

        assert result == {"id": "123", "name": "test-provider"}
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
                endpoint="/admin/providers",
                request=mock_request,
                current_user=mock_admin_token,
            )
        assert exc_info.value.status_code == 500

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("httpx.AsyncClient")
    async def test_proxy_handles_204_no_content(
        self, mock_client_class, mock_admin_token, mock_request
    ):
        """Test proxy handling of 204 No Content (DELETE responses)."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await proxy_to_gateway(
            method="DELETE",
            endpoint="/admin/providers/123",
            request=mock_request,
            current_user=mock_admin_token,
        )

        assert result == {}

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
                endpoint="/admin/providers",
                request=mock_request,
                current_user=mock_admin_token,
            )
        assert exc_info.value.status_code == 504

    async def test_proxy_blocks_non_admin(self, mock_analyst_token, mock_request):
        """Test that proxy blocks non-admin users."""
        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_gateway(
                method="GET",
                endpoint="/admin/providers",
                request=mock_request,
                current_user=mock_analyst_token,
            )
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestUpdateProvider:
    """Test update_provider endpoint."""

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("app.routers.admin_gateway_providers.proxy_to_gateway")
    async def test_update_provider_success(self, mock_proxy, mock_admin_token, mock_request):
        """Test successful provider update."""
        provider_id = uuid4()
        update_config = ProviderConfigUpdate(
            is_enabled=False,
            status="disabled",
        )

        mock_proxy.return_value = {
            "id": str(provider_id),
            "name": "test-provider",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "is_enabled": False,
            "status": "disabled",
            "priority": 100,
        }

        result = await update_provider(
            provider_id=provider_id,
            provider=update_config,
            request=mock_request,
            current_user=mock_admin_token,
        )

        assert isinstance(result, ProviderConfig)
        assert result.is_enabled is False
        assert result.status == "disabled"
        mock_proxy.assert_called_once()
        call_args = mock_proxy.call_args
        assert call_args.kwargs["method"] == "PUT"
        assert call_args.kwargs["endpoint"] == f"/admin/providers/{provider_id}"


@pytest.mark.asyncio
class TestDeleteProvider:
    """Test delete_provider endpoint."""

    @patch.dict("os.environ", {"GATEWAY_URL": "http://test-gateway:8002"})
    @patch("app.routers.admin_gateway_providers.proxy_to_gateway")
    async def test_delete_provider_success(self, mock_proxy, mock_admin_token, mock_request):
        """Test successful provider deletion."""
        provider_id = uuid4()
        mock_proxy.return_value = {}

        await delete_provider(
            provider_id=provider_id,
            request=mock_request,
            current_user=mock_admin_token,
        )

        mock_proxy.assert_called_once()
        call_args = mock_proxy.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert call_args.kwargs["endpoint"] == f"/admin/providers/{provider_id}"
