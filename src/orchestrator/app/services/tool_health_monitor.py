"""
Tool health monitoring service.

Tracks tool health, performs health checks, and manages circuit breaker state.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Tool, ToolHealthCheck
from ..schemas.tool import ToolStatus
from .secrets_manager import SecretsManager
from .tool_discovery_service import ToolDiscoveryService

logger = configure_logging(service_name="tool_health_monitor")


class ToolHealthMonitor:
    """Service for monitoring tool health."""

    def __init__(self, db: AsyncSession):
        """
        Initialize health monitor.

        Args:
            db: Database session
        """
        self.db = db
        self.discovery_service = ToolDiscoveryService(db)
        self.secrets_manager = SecretsManager(db)
        self._running = False
        self._task: asyncio.Task | None = None

    async def check_tool_health(self, tool_id: UUID) -> ToolHealthCheck:
        """
        Perform health check on a tool.

        Attempts to connect to MCP server and verify responsiveness.

        Args:
            tool_id: Tool UUID

        Returns:
            ToolHealthCheck record

        Raises:
            ValueError: If tool not found
        """
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        health_check = ToolHealthCheck(
            tool_id=tool_id,
            status=ToolStatus.UNKNOWN.value,
            checked_at=datetime.now(UTC),
        )

        try:
            # Create MCP client
            client = self.discovery_service.create_mcp_client(tool)

            # Retrieve secrets if needed
            if tool.requires_authentication and tool.secret_name:
                secret_value = await self.secrets_manager.retrieve_secret(tool.secret_name)
                if secret_value:
                    if hasattr(client, "set_auth_token"):
                        client.set_auth_token(secret_value)  # type: ignore[attr-defined]
                    elif hasattr(client, "auth_token"):
                        client.auth_token = secret_value  # type: ignore[attr-defined]
                    else:
                        logger.warning(
                            "Tool %s requires auth but client doesn't support it",
                            tool.tool_id,
                        )

            # Perform health check
            start_time = datetime.now(UTC)
            await client.connect()

            # Try to initialize
            init_result = await client.initialize()

            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            health_check.status = ToolStatus.ONLINE.value
            health_check.response_time_ms = response_time
            health_check.mcp_server_info = init_result

            # Update tool status
            tool.is_healthy = True
            tool.last_health_check = datetime.now(UTC)

            await client.disconnect()

            logger.info("Health check passed: %s (%.2fms)", tool.tool_id, response_time)

        except TimeoutError:
            health_check.status = ToolStatus.OFFLINE.value
            health_check.error_message = "Connection timeout"
            health_check.error_code = "TIMEOUT"
            tool.is_healthy = False
            tool.last_health_check = datetime.now(UTC)
            logger.error("Health check timeout: %s", tool.tool_id)

        except Exception as e:
            health_check.status = ToolStatus.OFFLINE.value
            health_check.error_message = str(e)
            health_check.error_code = type(e).__name__
            tool.is_healthy = False
            tool.last_health_check = datetime.now(UTC)
            logger.error("Health check failed: %s: %s", tool.tool_id, e)

        self.db.add(health_check)
        await self.db.commit()
        await self.db.refresh(health_check)

        return health_check

    async def check_all_enabled_tools(self) -> dict[UUID, ToolHealthCheck]:
        """
        Check health of all enabled tools.

        Returns:
            Dict mapping tool_id to health check result
        """
        stmt = select(Tool).where(Tool.is_enabled == True)  # noqa: E712
        result = await self.db.execute(stmt)
        tools = result.scalars().all()

        results: dict[UUID, ToolHealthCheck] = {}

        for tool in tools:
            try:
                health_check = await self.check_tool_health(tool.id)
                results[tool.id] = health_check
            except Exception as e:
                logger.error("Failed to check health for %s: %s", tool.tool_id, e)

        return results

    async def periodic_health_checks(self, interval_seconds: int = 300) -> None:
        """
        Background task: Periodically check tool health.

        Args:
            interval_seconds: Interval between checks (default 5 minutes)
        """
        self._running = True
        logger.info("Starting periodic health checks...")

        while self._running:
            try:
                logger.debug("Running periodic health checks...")
                results = await self.check_all_enabled_tools()

                online = sum(1 for h in results.values() if h.status == ToolStatus.ONLINE.value)
                total = len(results)

                logger.info("Health checks complete: %d/%d tools online", online, total)

            except Exception as e:
                logger.error("Periodic health check failed: %s", e)

            # Wait for next interval
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("Periodic health checks cancelled")
                break

        logger.info("Periodic health checks stopped")

    def start_periodic_checks(self, interval_seconds: int = 300) -> None:
        """
        Start periodic health checks in background.

        Args:
            interval_seconds: Interval between checks (default 5 minutes)
        """
        if self._running or self._task is not None:
            logger.warning("Periodic health checks already running")
            return

        self._task = asyncio.create_task(self.periodic_health_checks(interval_seconds))
        logger.info("Periodic health checks started")

    def stop_periodic_checks(self) -> None:
        """Stop periodic health checks."""
        if not self._running:
            logger.warning("Periodic health checks not running")
            return

        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Periodic health checks stopped")
