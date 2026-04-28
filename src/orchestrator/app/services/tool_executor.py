"""
Tool execution service.

Executes MCP tool calls with retries, circuit breakers, and observability.
"""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Tool, ToolInvocation, ToolPermission
from ..mcp.base_client import MCPClient
from ..schemas.tool import InvocationStatus
from ..services.tool_discovery_service import ToolDiscoveryService
from ..services.tool_permission_service import ToolPermissionService
from .secrets_manager import SecretsManager

logger = configure_logging(service_name="tool_executor")


class CircuitBreaker:
    """
    Circuit breaker for tool calls.

    Prevents cascading failures by tracking error rates.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to keep circuit open
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures: dict[str, list[datetime]] = {}
        self.open_until: dict[str, datetime] = {}

    def is_open(self, tool_id: str) -> bool:
        """
        Check if circuit is open (blocking calls).

        Args:
            tool_id: Tool identifier

        Returns:
            True if circuit is open, False otherwise
        """
        if tool_id in self.open_until:
            if datetime.now(UTC) < self.open_until[tool_id]:
                return True
            # Timeout expired, close circuit
            del self.open_until[tool_id]
            self.failures[tool_id] = []

        return False

    def record_success(self, tool_id: str) -> None:
        """
        Record successful call (resets failures).

        Args:
            tool_id: Tool identifier
        """
        if tool_id in self.failures:
            self.failures[tool_id] = []

    def record_failure(self, tool_id: str) -> None:
        """
        Record failed call (may open circuit).

        Args:
            tool_id: Tool identifier
        """
        now = datetime.now(UTC)

        if tool_id not in self.failures:
            self.failures[tool_id] = []

        # Add failure
        self.failures[tool_id].append(now)

        # Remove old failures (outside window)
        window_start = now - timedelta(seconds=300)  # 5 minute window
        self.failures[tool_id] = [f for f in self.failures[tool_id] if f > window_start]

        # Check if threshold exceeded
        if len(self.failures[tool_id]) >= self.failure_threshold:
            self.open_until[tool_id] = now + timedelta(seconds=self.timeout_seconds)
            logger.warning(f"Circuit breaker opened for tool: {tool_id}")


class ToolExecutor:
    """Service for executing MCP tool calls."""

    def __init__(self, db: AsyncSession):
        """
        Initialize tool executor.

        Args:
            db: Database session
        """
        self.db = db
        self.discovery_service = ToolDiscoveryService(db)
        self.permission_service = ToolPermissionService(db)
        self.secrets_manager = SecretsManager(db)
        self.circuit_breaker = CircuitBreaker()
        self.active_clients: dict[str, MCPClient] = {}

    async def execute_tool(
        self,
        tool_id: UUID,
        tool_name: str,
        parameters: dict[str, Any],
        user_id: UUID,
        user_role: str | None = None,
        user_roles: list[str] | None = None,
        run_id: str | None = None,
        use_case_id: UUID | None = None,
        center_id: str | None = None,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """
        Execute a tool call with full observability.

        Args:
            tool_id: Tool UUID
            tool_name: Name of the specific tool to call
            parameters: Tool parameters
            user_id: User invoking the tool
            user_role: User's role (deprecated, use user_roles for multi-role support)
            user_roles: List of user's roles (preferred for multi-role support per ADR-060)
            run_id: Request ID for tracking
            use_case_id: Use case context
            center_id: Center ID for quota tracking
            max_retries: Retry attempts on failure

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or invalid
            RuntimeError: If tool disabled or circuit breaker open
            PermissionError: If user lacks permission

        Note:
            If both user_role and user_roles are provided, user_roles takes precedence.
            Admin role in user_roles bypasses all permission checks.
        """
        # Load tool configuration
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        # Check if enabled
        if not tool.is_enabled:
            raise RuntimeError(f"Tool {tool.tool_id} is disabled")

        # Check circuit breaker
        if self.circuit_breaker.is_open(str(tool_id)):
            raise RuntimeError(f"Circuit breaker open for tool {tool.tool_id}")

        # Determine roles to check (prefer user_roles, fallback to user_role for backward compatibility)
        roles_to_check: list[str] = []
        if user_roles:
            roles_to_check = user_roles
        elif user_role:
            roles_to_check = [user_role]
        else:
            roles_to_check = ["user"]  # Default fallback

        # Check permissions using multi-role support
        can_use = await self.permission_service.check_permission_for_roles(
            tool_id,
            roles_to_check,
            "use",
        )

        if not can_use:
            roles_str = ", ".join(roles_to_check)
            raise PermissionError(f"Roles [{roles_str}] not permitted to use tool {tool.tool_id}")

        # Check rate limits (use first role for rate limiting, or "user" as fallback)
        rate_limit_role = roles_to_check[0] if roles_to_check else "user"
        await self._check_rate_limits(tool_id, user_id, rate_limit_role)

        # Create audit record
        invocation = ToolInvocation(
            tool_id=tool_id,
            use_case_id=use_case_id,
            run_id=run_id,
            user_id=user_id,
            center_id=center_id,
            tool_name=tool_name,
            tool_parameters=parameters,
            status=InvocationStatus.SUCCESS.value,
            started_at=datetime.now(UTC),
        )
        self.db.add(invocation)
        await self.db.flush()

        # Execute with retries
        for attempt in range(max_retries + 1):
            try:
                start_time = datetime.now(UTC)

                # Get or create MCP client
                client = await self._get_mcp_client(tool)

                # Execute tool call
                result = await client.call_tool(tool_name, parameters)

                # Success
                duration = (datetime.now(UTC) - start_time).total_seconds() * 1000

                invocation.status = InvocationStatus.SUCCESS.value
                invocation.response_data = (
                    result if isinstance(result, dict) else {"result": result}
                )
                invocation.completed_at = datetime.now(UTC)
                invocation.duration_ms = duration
                invocation.mcp_protocol_version = tool.mcp_protocol_version

                self.circuit_breaker.record_success(str(tool_id))

                await self.db.commit()

                logger.info(
                    f"Tool executed successfully: {tool.tool_id}/{tool_name} in {duration:.2f}ms"
                )

                return result if isinstance(result, dict) else {"result": result}

            except Exception as e:
                logger.error(f"Tool execution failed (attempt {attempt + 1}): {e}")

                if attempt >= max_retries:
                    # Final failure
                    duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    invocation.status = InvocationStatus.ERROR.value
                    invocation.error_message = str(e)
                    invocation.completed_at = datetime.now(UTC)
                    invocation.duration_ms = duration
                    invocation.mcp_protocol_version = tool.mcp_protocol_version

                    self.circuit_breaker.record_failure(str(tool_id))

                    await self.db.commit()
                    raise

                # Retry with exponential backoff
                await asyncio.sleep(2**attempt)

        # Should never reach here, but satisfy type checker
        raise RuntimeError("Tool execution failed after all retries")

    async def _get_mcp_client(self, tool: Tool) -> MCPClient:
        """
        Get or create MCP client for tool.

        Args:
            tool: Tool database record

        Returns:
            Connected and initialized MCP client

        Raises:
            ConnectionError: If client connection fails
            ValueError: If client initialization fails
        """
        tool_id = str(tool.id)

        if tool_id in self.active_clients:
            client = self.active_clients[tool_id]
            # Verify client is still initialized
            if client.is_initialized:
                return client
            # Client lost connection, remove and recreate
            with contextlib.suppress(Exception):
                await client.disconnect()
            del self.active_clients[tool_id]

        # Create new client
        client = self.discovery_service.create_mcp_client(tool)

        # Retrieve secrets if needed
        if tool.requires_authentication and tool.secret_name:
            secret_value = await self.secrets_manager.retrieve_secret(tool.secret_name)
            if secret_value:
                # Inject secret into client configuration
                # For HTTP clients, this might be headers or auth params
                # For STDIO clients, this might be environment variables
                # Implementation depends on authentication type
                # For now, we'll store it in client config if supported
                if hasattr(client, "set_auth_token"):
                    client.set_auth_token(secret_value)  # type: ignore[attr-defined]
                elif hasattr(client, "auth_token"):
                    client.auth_token = secret_value  # type: ignore[attr-defined]
                else:
                    logger.warning(
                        f"Tool {tool.tool_id} requires auth but client doesn't support it"
                    )

        await client.connect()
        await client.initialize()

        self.active_clients[tool_id] = client

        return client

    async def _check_rate_limits(
        self,
        tool_id: UUID,
        user_id: UUID,
        user_role: str,
    ) -> None:
        """
        Check if user has exceeded rate limits.

        Args:
            tool_id: Tool UUID
            user_id: User UUID
            user_role: User role

        Raises:
            RuntimeError: If rate limit exceeded
        """
        # Get permission with rate limits
        stmt = select(ToolPermission).where(
            ToolPermission.tool_id == tool_id,
            ToolPermission.role == user_role,
        )
        result = await self.db.execute(stmt)
        permission = result.scalar_one_or_none()

        if not permission:
            return

        # Check hourly limit
        if permission.max_calls_per_hour:
            hour_ago = datetime.now(UTC) - timedelta(hours=1)
            count_stmt = (
                select(func.count())
                .select_from(ToolInvocation)
                .where(
                    ToolInvocation.tool_id == tool_id,
                    ToolInvocation.user_id == user_id,
                    ToolInvocation.started_at > hour_ago,
                )
            )
            result = await self.db.execute(count_stmt)
            recent_calls = result.scalar() or 0

            if recent_calls >= permission.max_calls_per_hour:
                raise RuntimeError(
                    f"Rate limit exceeded: {permission.max_calls_per_hour} calls/hour"
                )

        # Check daily limit
        if permission.max_calls_per_day:
            day_ago = datetime.now(UTC) - timedelta(days=1)
            count_stmt = (
                select(func.count())
                .select_from(ToolInvocation)
                .where(
                    ToolInvocation.tool_id == tool_id,
                    ToolInvocation.user_id == user_id,
                    ToolInvocation.started_at > day_ago,
                )
            )
            result = await self.db.execute(count_stmt)
            recent_calls = result.scalar() or 0

            if recent_calls >= permission.max_calls_per_day:
                raise RuntimeError(f"Rate limit exceeded: {permission.max_calls_per_day} calls/day")

    async def cleanup(self) -> None:
        """Cleanup active MCP clients."""
        for client in self.active_clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting client: {e}")

        self.active_clients.clear()
        logger.info("Tool executor cleanup complete")
