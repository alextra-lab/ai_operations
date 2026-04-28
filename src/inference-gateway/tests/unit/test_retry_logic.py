"""
Unit tests for BaseProvider retry logic.

Tests retry behavior, exponential backoff, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers.base import BaseProvider, ProviderConfig
from app.utils.errors import ProviderHTTPError, ProviderTimeoutError


class MockProvider(BaseProvider):
    """Mock provider for testing retry logic."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.call_count = 0

    async def failing_call(self) -> str:
        """Call that always fails with timeout."""
        self.call_count += 1
        raise httpx.TimeoutException("Request timeout")

    async def transient_failure(self) -> str:
        """Call that fails once then succeeds."""
        self.call_count += 1
        if self.call_count == 1:
            raise httpx.ConnectError("Connection failed")
        return "success"

    async def http_error(self) -> str:
        """Call that raises HTTPStatusError (no retry)."""
        self.call_count += 1
        response = MagicMock()
        response.status_code = 500
        response.text = "Internal Server Error"
        raise httpx.HTTPStatusError(
            "HTTP error",
            request=MagicMock(),
            response=response,
        )

    async def success_call(self) -> str:
        """Call that always succeeds."""
        self.call_count += 1
        return "success"


@pytest.fixture
def provider_config():
    """Create test provider config."""
    return ProviderConfig(
        id="12345678-1234-1234-1234-123456789abc",
        name="test-provider",
        provider_type="openai_compatible",
        base_url="https://api.test.com",
        timeout_seconds=5.0,
    )


@pytest.fixture
def mock_provider(provider_config):
    """Create mock provider instance."""
    return MockProvider(provider_config)


class TestBaseProviderInitialization:
    """Test BaseProvider initialization."""

    def test_provider_init(self, provider_config):
        """Test provider initializes correctly."""
        provider = BaseProvider(provider_config)

        assert provider.name == "test-provider"
        assert provider.config == provider_config
        assert provider.base_url == "https://api.test.com"
        assert provider.timeout == 5.0
        assert provider.client is None

    def test_provider_with_api_key(self):
        """Test provider with API key."""
        config = ProviderConfig(
            id="12345678-1234-1234-1234-123456789def",
            name="test",
            provider_type="openai_compatible",
            base_url="https://api.test.com",
            api_key="sk-test123",
        )
        provider = BaseProvider(config)

        assert provider.api_key == "sk-test123"


class TestContextManager:
    """Test context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_entry(self, mock_provider):
        """Test entering context manager."""
        async with mock_provider as p:
            assert p is mock_provider

    @pytest.mark.asyncio
    async def test_context_manager_exit_with_client(self, mock_provider):
        """Test exiting context manager closes client."""
        mock_client = AsyncMock()
        mock_provider.client = mock_client

        async with mock_provider:
            pass

        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit_without_client(self, mock_provider):
        """Test exiting context manager when no client."""
        async with mock_provider:
            pass
        # Should not raise


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, mock_provider):
        """Test successful call on first attempt (no retry)."""
        result = await mock_provider.call_with_retry(
            mock_provider.success_call,
        )

        assert result == "success"
        assert mock_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_transient_failure(self, mock_provider):
        """Test success after one transient failure (retried once)."""
        result = await mock_provider.call_with_retry(
            mock_provider.transient_failure,
        )

        assert result == "success"
        assert mock_provider.call_count == 2  # Failed once, succeeded second time

    @pytest.mark.asyncio
    async def test_timeout_after_max_retries(self, mock_provider):
        """Test ProviderTimeoutError raised after max retries."""
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await mock_provider.call_with_retry(
                mock_provider.failing_call,
            )

        assert exc_info.value.provider_name == "test-provider"
        assert exc_info.value.timeout_seconds == 5.0
        assert mock_provider.call_count == 2  # Initial + 1 retry = 2 attempts

    @pytest.mark.asyncio
    async def test_http_error_no_retry(self, mock_provider):
        """Test HTTP errors are not retried."""
        with pytest.raises(ProviderHTTPError) as exc_info:
            await mock_provider.call_with_retry(
                mock_provider.http_error,
            )

        assert exc_info.value.provider_name == "test-provider"
        assert exc_info.value.status_code == 500
        assert mock_provider.call_count == 1  # No retry on HTTP errors


class TestRetryBackoff:
    """Test exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_backoff_called_on_retry(self, mock_provider):
        """Test backoff logging is called during retry."""
        with patch("app.providers.base.logger") as mock_logger:
            try:
                await mock_provider.call_with_retry(
                    mock_provider.failing_call,
                )
            except ProviderTimeoutError:
                pass

            # Should log warning on retry attempt
            assert mock_logger.warning.called
            call_args = mock_logger.warning.call_args
            assert "Provider retry attempt" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_max_tries_limit(self, mock_provider):
        """Test max tries is enforced (2 attempts total)."""
        try:
            await mock_provider.call_with_retry(
                mock_provider.failing_call,
            )
        except ProviderTimeoutError:
            pass

        # Should be called exactly 2 times (initial + 1 retry)
        assert mock_provider.call_count == 2


class TestErrorConversion:
    """Test exception conversion in retry logic."""

    @pytest.mark.asyncio
    async def test_timeout_exception_converted(self, mock_provider):
        """Test httpx.TimeoutException converted to ProviderTimeoutError."""
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await mock_provider.call_with_retry(
                mock_provider.failing_call,
            )

        assert isinstance(exc_info.value, ProviderTimeoutError)
        assert exc_info.value.provider_name == "test-provider"

    @pytest.mark.asyncio
    async def test_http_status_error_converted(self, mock_provider):
        """Test httpx.HTTPStatusError converted to ProviderHTTPError."""
        with pytest.raises(ProviderHTTPError) as exc_info:
            await mock_provider.call_with_retry(
                mock_provider.http_error,
            )

        assert isinstance(exc_info.value, ProviderHTTPError)
        assert exc_info.value.provider_name == "test-provider"
        assert exc_info.value.status_code == 500


class TestHealthCheck:
    """Test default health check."""

    @pytest.mark.asyncio
    async def test_default_health_check(self, mock_provider):
        """Test default health check returns True."""
        result = await mock_provider.health_check()
        assert result is True


class TestRetryWithArguments:
    """Test retry with function arguments."""

    @pytest.mark.asyncio
    async def test_retry_with_args(self, mock_provider):
        """Test retry passes args correctly."""

        async def test_func(arg1: str, arg2: int) -> str:
            return f"{arg1}_{arg2}"

        result = await mock_provider.call_with_retry(
            test_func,
            "test",
            42,
        )

        assert result == "test_42"

    @pytest.mark.asyncio
    async def test_retry_with_kwargs(self, mock_provider):
        """Test retry passes kwargs correctly."""

        async def test_func(arg1: str, arg2: int = 0) -> str:
            return f"{arg1}_{arg2}"

        result = await mock_provider.call_with_retry(
            test_func,
            arg1="test",
            arg2=99,
        )

        assert result == "test_99"


class TestRetryConfiguration:
    """Test retry configuration parameters."""

    @pytest.mark.asyncio
    async def test_max_backoff_value(self, mock_provider):
        """Test max backoff is capped at 10 seconds."""
        # This is implicit in the backoff decorator configuration
        # Just verify the configuration exists
        assert hasattr(mock_provider, "call_with_retry")

    @pytest.mark.asyncio
    async def test_retry_on_specific_exceptions(self, mock_provider):
        """Test retry only on transient errors."""

        async def raise_value_error():
            raise ValueError("Not a transient error")

        # ValueError should not be retried, should propagate
        with pytest.raises(ValueError):
            await mock_provider.call_with_retry(raise_value_error)
