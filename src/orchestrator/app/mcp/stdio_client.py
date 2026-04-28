"""
STDIO MCP client implementation.

Supports MCP servers that communicate via standard input/output (subprocess).
"""

import asyncio
import contextlib
import json
from types import TracebackType
from typing import Self

from shared.logging_utils.fastapi import configure_logging

from .base_client import MCPClient
from .protocol_handler import MCPRequest, MCPResponse

logger = configure_logging(service_name="mcp_stdio_client")


class StdioMCPClient(MCPClient):
    """
    STDIO-based MCP client.

    Communicates with MCP server via subprocess stdin/stdout.
    """

    def __init__(
        self,
        command: list[str],
        protocol_version: str = "2024-11-05",
        timeout_seconds: int = 30,
        env: dict[str, str] | None = None,
    ):
        """
        Initialize STDIO MCP client.

        Args:
            command: Command and arguments to start MCP server subprocess
            protocol_version: MCP protocol version
            timeout_seconds: Request timeout in seconds
            env: Optional environment variables for subprocess
        """
        super().__init__(protocol_version)
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.env = env
        self._process: asyncio.subprocess.Process | None = None
        self._request_id_counter = 0
        self._pending_requests: dict[str | int, asyncio.Future[MCPResponse]] = {}
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """
        Start MCP server subprocess and establish STDIO communication.

        Raises:
            ConnectionError: If subprocess fails to start
        """
        if not self.command:
            raise ValueError("MCP command is required for STDIO client")

        try:
            # Start subprocess
            self._process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            if not self._process.stdin or not self._process.stdout:
                raise ConnectionError("Failed to create subprocess pipes")

            # Start reader task to process responses
            self._reader_task = asyncio.create_task(self._read_responses())

            logger.info(f"STDIO MCP client connected: {' '.join(self.command)}")

        except Exception as e:
            logger.error(f"Failed to start MCP subprocess: {e}")
            raise ConnectionError(f"Failed to start MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Terminate MCP server subprocess and close communication."""
        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task

        # Terminate subprocess
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                # Force kill if termination times out
                self._process.kill()
                await self._process.wait()
            except Exception as e:
                logger.warning(f"Error terminating MCP subprocess: {e}")

            self._process = None

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()

        self._pending_requests.clear()
        logger.info("STDIO MCP client disconnected")

    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Send request via stdin and wait for response via stdout.

        Args:
            request: MCP request message

        Returns:
            MCP response message

        Raises:
            ConnectionError: If connection is not established
            TimeoutError: If request times out
            ValueError: If response is invalid
        """
        if not self._process or not self._process.stdin:
            raise ConnectionError("STDIO client not connected. Call connect() first.")

        # Ensure request has an ID
        if request.id is None:
            self._request_id_counter += 1
            request.id = self._request_id_counter

        # Create future for response
        future: asyncio.Future[MCPResponse] = asyncio.Future()
        self._pending_requests[request.id] = future

        try:
            # Serialize and send request
            request_json = request.to_json() + "\n"  # MCP uses newline-delimited JSON
            self._process.stdin.write(request_json.encode("utf-8"))
            await self._process.stdin.drain()

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=self.timeout_seconds)

            # Validate response
            self.protocol_handler.validate_response(response, request.id)

            return response

        except TimeoutError:
            self._pending_requests.pop(request.id, None)
            raise TimeoutError(f"MCP request timed out after {self.timeout_seconds}s") from None
        except Exception as e:
            self._pending_requests.pop(request.id, None)
            logger.error(f"MCP request failed: {e}")
            raise ConnectionError(f"MCP request failed: {e}") from e

    async def _read_responses(self) -> None:
        """
        Background task: Read responses from stdout and complete pending requests.

        Processes newline-delimited JSON responses from MCP server.
        """
        if not self._process or not self._process.stdout:
            return

        buffer = ""

        try:
            while True:
                # Read chunk
                chunk = await self._process.stdout.read(4096)
                if not chunk:
                    break  # EOF

                # Decode and add to buffer
                buffer += chunk.decode("utf-8", errors="replace")

                # Process complete lines (newline-delimited JSON)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        # Parse MCP response
                        response = self.protocol_handler.parse_response(line)

                        # Complete pending request
                        if response.id in self._pending_requests:
                            future = self._pending_requests.pop(response.id)
                            if not future.done():
                                future.set_result(response)
                        else:
                            logger.warning(
                                f"Received response for unknown request ID: {response.id}"
                            )

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Failed to parse MCP response line: {e}")
                        logger.debug(f"Response line: {line}")

        except asyncio.CancelledError:
            logger.info("STDIO response reader cancelled")
        except Exception as e:
            logger.error(f"Error reading MCP responses: {e}")
            # Cancel all pending requests
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(ConnectionError(f"Reader error: {e}"))
            self._pending_requests.clear()

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
