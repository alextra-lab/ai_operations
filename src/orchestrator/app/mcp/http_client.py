"""
HTTP/SSE MCP client implementation.

Supports MCP servers accessible via HTTP or Server-Sent Events (SSE).
"""

from types import TracebackType
from typing import Self

import httpx

from shared.logging_utils.fastapi import configure_logging

from .base_client import MCPClient
from .protocol_handler import MCPRequest, MCPResponse

logger = configure_logging(service_name="mcp_http_client")


class HTTPMCPClient(MCPClient):
    """
    HTTP-based MCP client.

    Supports both HTTP POST requests and SSE (Server-Sent Events) for streaming.
    """

    def __init__(
        self,
        endpoint: str,
        protocol_version: str = "2024-11-05",
        timeout_seconds: int = 30,
        headers: dict[str, str] | None = None,
    ):
        """
        Initialize HTTP MCP client.

        Args:
            endpoint: MCP server endpoint URL
            protocol_version: MCP protocol version
            timeout_seconds: Request timeout in seconds
            headers: Optional HTTP headers (e.g., for authentication)
        """
        super().__init__(protocol_version)
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Establish HTTP connection (no-op for HTTP, validates endpoint)."""
        if not self.endpoint:
            raise ValueError("MCP endpoint URL is required")

        # Create HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers=self.headers,
        )

        # Validate endpoint is reachable (optional health check)
        try:
            # Try a simple GET to check connectivity
            response = await self._client.get(self.endpoint, timeout=5.0)
            if response.status_code >= 400:
                logger.warning(f"MCP endpoint returned {response.status_code}: {self.endpoint}")
        except httpx.RequestError as e:
            logger.warning(f"Could not reach MCP endpoint: {e}")
            # Don't fail - endpoint might require POST only

        logger.info(f"HTTP MCP client connected to: {self.endpoint}")

    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP MCP client disconnected")

    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send HTTP POST request to MCP server.

        Args:
            request: MCP request message

        Returns:
            MCP response message

        Raises:
            ConnectionError: If connection is not established
            TimeoutError: If request times out
            ValueError: If response is invalid
        """
        if not self._client:
            raise ConnectionError("HTTP client not connected. Call connect() first.")

        # Serialize request
        request_json = request.to_json()

        try:
            # Merge request headers with default headers (including Authorization if set)
            request_headers = {"Content-Type": "application/json"}
            if self.headers:
                request_headers.update(self.headers)

            # Send POST request
            response = await self._client.post(
                self.endpoint,
                content=request_json,
                headers=request_headers,
            )

            # Check HTTP status
            response.raise_for_status()

            # Parse MCP response
            mcp_response = self.protocol_handler.parse_response(response.text)

            # Validate response matches request
            self.protocol_handler.validate_response(mcp_response, request.id)

            return mcp_response

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = e.response.text[:500] if e.response.text else "No error details"

            if status_code == 401:
                error_msg = (
                    f"Authentication failed (401 Unauthorized). "
                    f"Please verify your API key or credentials. Details: {error_detail}"
                )
            elif status_code == 403:
                error_msg = (
                    f"Authorization failed (403 Forbidden). "
                    f"Your credentials are valid but lack required permissions. Details: {error_detail}"
                )
            else:
                error_msg = f"HTTP error {status_code}: {error_detail}"

            logger.error(
                f"MCP request HTTP error {status_code}: {error_msg}",
                extra={"status_code": status_code, "endpoint": self.endpoint},
            )
            raise ConnectionError(error_msg) from e
        except httpx.TimeoutException as e:
            logger.error(f"MCP request timeout: {e}")
            raise TimeoutError(f"MCP request timed out after {self.timeout_seconds}s") from e
        except httpx.RequestError as e:
            logger.error(f"MCP request failed: {e}")
            raise ConnectionError(f"MCP request failed: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid MCP response: {e}")
            raise

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()
