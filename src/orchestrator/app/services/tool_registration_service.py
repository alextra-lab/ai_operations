"""
Tool registration service.

Manages multi-phase tool registration workflow with validation,
connection testing, and atomic commit.
"""

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Tool
from ..schemas.tool import MCPServerType, ToolCreate
from ..schemas.tool_registration import (
    BasicInfoData,
    CommitData,
    ConnectionTestData,
    McpConfigData,
    PermissionsData,
    ReviewData,
    SecurityConfigData,
    ToolRegistrationPhase,
)
from .secrets_manager import SecretsManager
from .tool_discovery_service import ToolDiscoveryService
from .tool_permission_service import ToolPermissionService
from .tool_service import ToolService

logger = configure_logging(service_name="tool_registration_service")


@dataclass
class RegistrationSession:
    """In-memory registration session state."""

    session_id: str
    user_id: uuid.UUID
    current_phase: ToolRegistrationPhase
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    # Phase data
    basic_info: dict[str, Any] | None = None
    mcp_config: dict[str, Any] | None = None
    connection_result: dict[str, Any] | None = None
    security_config: dict[str, Any] | None = None
    permissions_config: dict[str, Any] | None = None

    # Validation state
    validation_errors: dict[str, list[str]] = field(default_factory=dict)
    can_proceed: bool = False


class ToolRegistrationService:
    """Service for managing tool registration workflow."""

    # In-memory session store (TODO: Replace with Redis for production)
    _sessions: ClassVar[dict[str, RegistrationSession]] = {}

    def __init__(self, db: AsyncSession):
        """Initialize registration service."""
        self.db = db
        self.tool_service = ToolService(db)
        self.discovery_service = ToolDiscoveryService(db)
        self.secrets_manager = SecretsManager(db)
        self.permission_service = ToolPermissionService(db)

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return secrets.token_urlsafe(32)

    def _create_session(self, user_id: uuid.UUID) -> RegistrationSession:
        """Create new registration session."""
        session_id = self._generate_session_id()
        now = datetime.now(UTC)

        session = RegistrationSession(
            session_id=session_id,
            user_id=user_id,
            current_phase=ToolRegistrationPhase.BASIC_INFO,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
        )

        self._sessions[session_id] = session
        logger.info(f"Created registration session: {session_id}")

        return session

    def _get_session(self, session_id: str) -> RegistrationSession:
        """
        Retrieve registration session.

        Raises:
            ValueError: If session not found or expired
        """
        session = self._sessions.get(session_id)

        if not session:
            raise ValueError(f"Registration session '{session_id}' not found")

        if datetime.now(UTC) > session.expires_at:
            del self._sessions[session_id]
            raise ValueError(f"Registration session '{session_id}' has expired")

        return session

    def _update_session(self, session: RegistrationSession) -> None:
        """Update session in store."""
        session.updated_at = datetime.now(UTC)
        self._sessions[session.session_id] = session

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        now = datetime.now(UTC)
        expired = [sid for sid, sess in self._sessions.items() if now > sess.expires_at]

        for sid in expired:
            del self._sessions[sid]
            logger.info(f"Cleaned up expired session: {sid}")

    def _get_next_phase(
        self,
        current_phase: ToolRegistrationPhase,
    ) -> ToolRegistrationPhase | None:
        """Determine next phase in workflow."""
        phase_order = [
            ToolRegistrationPhase.BASIC_INFO,
            ToolRegistrationPhase.MCP_CONFIG,
            ToolRegistrationPhase.SECURITY_CONFIG,
            ToolRegistrationPhase.CONNECTION_TEST,
            ToolRegistrationPhase.PERMISSIONS,
            ToolRegistrationPhase.REVIEW,
            ToolRegistrationPhase.COMMIT,
        ]

        try:
            current_index = phase_order.index(current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            pass

        return None

    # Phase handlers

    async def _handle_basic_info(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 1: Basic Information.

        Validates basic tool information and checks tool_id uniqueness.
        """
        # Parse and validate data
        try:
            basic_data = BasicInfoData(**data)
        except Exception as e:
            session.validation_errors["basic_info"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        # Check tool_id uniqueness
        existing = await self.tool_service.get_tool(basic_data.tool_id)
        if existing:
            session.validation_errors["basic_info"] = [
                f"Tool ID '{basic_data.tool_id}' already exists"
            ]
            session.can_proceed = False
            return {
                "success": False,
                "error": f"Tool ID '{basic_data.tool_id}' already exists",
            }

        # Store validated data
        session.basic_info = basic_data.model_dump()
        session.validation_errors.pop("basic_info", None)
        session.can_proceed = True

        logger.info(f"Basic info validated for session {session.session_id}")

        return {"success": True}

    async def _handle_mcp_config(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 2: MCP Configuration.

        Validates MCP server configuration.
        """
        # Parse and validate data
        try:
            mcp_data = McpConfigData(**data)
        except Exception as e:
            session.validation_errors["mcp_config"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        # Validate server type specific requirements
        server_type = mcp_data.mcp_server_type

        if server_type == MCPServerType.STDIO.value:
            if not mcp_data.mcp_command:
                error_msg = "stdio server type requires mcp_command"
                session.validation_errors["mcp_config"] = [error_msg]
                session.can_proceed = False
                return {"success": False, "error": error_msg}

        elif (
            server_type in [MCPServerType.HTTP.value, MCPServerType.SSE.value]
            and not mcp_data.mcp_endpoint
        ):
            error_msg = f"{server_type} server type requires mcp_endpoint"
            session.validation_errors["mcp_config"] = [error_msg]
            session.can_proceed = False
            return {"success": False, "error": error_msg}

        # Store validated data
        session.mcp_config = mcp_data.model_dump()
        session.validation_errors.pop("mcp_config", None)
        session.can_proceed = True

        logger.info(f"MCP config validated for session {session.session_id}")

        return {"success": True}

    async def _handle_connection_test(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 3: Connection Testing.

        Tests connection to MCP server and discovers capabilities.
        """
        try:
            test_data = ConnectionTestData(**data)
        except Exception as e:
            session.validation_errors["connection_test"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        if test_data.action == "skip":
            # Allow skipping connection test (expert mode)
            session.connection_result = {
                "tested": False,
                "skipped": True,
                "warning": "Connection not tested - tool may not work correctly",
            }
            session.validation_errors.pop("connection_test", None)
            session.can_proceed = True

            logger.warning(f"Connection test skipped for session {session.session_id}")

            return {
                "success": True,
                "skipped": True,
                "warning": "Connection not tested - tool may not work correctly",
            }

        # Perform connection test
        # Validate required phase data exists
        if not session.basic_info:
            error_msg = "Basic info required before connection test"
            session.validation_errors["connection_test"] = [error_msg]
            session.can_proceed = False
            return {"success": False, "error": error_msg}

        if not session.mcp_config:
            error_msg = "MCP config required before connection test"
            session.validation_errors["connection_test"] = [error_msg]
            session.can_proceed = False
            return {"success": False, "error": error_msg}

        # Security config should exist now (since we moved it before connection test)
        # But allow connection test without auth for tools that don't require it
        if not session.security_config:
            logger.warning(
                f"No security config found for session {session.session_id} - "
                "connection test will proceed without authentication"
            )

        # Create temporary tool object for testing
        import json

        temp_tool = Tool(
            id=uuid.uuid4(),
            tool_id=session.basic_info["tool_id"],
            name=session.basic_info["name"],
            description=session.basic_info.get("description"),
            category=session.basic_info["category"],
            provider=session.basic_info.get("provider"),
            tool_purpose=session.basic_info["tool_purpose"],
            service_location=session.basic_info["service_location"],
            mcp_server_type=session.mcp_config["mcp_server_type"],
            mcp_command=(
                json.dumps(session.mcp_config.get("mcp_command"))
                if session.mcp_config.get("mcp_command")
                else None
            ),
            mcp_endpoint=session.mcp_config.get("mcp_endpoint"),
            mcp_protocol_version=session.mcp_config["mcp_protocol_version"],
            timeout_seconds=session.mcp_config["timeout_seconds"],
            requires_authentication=(
                session.security_config.get("requires_authentication", False)
                if session.security_config
                else False
            ),
            authentication_type=(
                session.security_config.get("authentication_type")
                if session.security_config
                else None
            ),
            secret_name=(
                session.security_config.get("secret_name") if session.security_config else None
            ),
            is_enabled=False,
            is_healthy=False,
        )

        try:
            # Attempt discovery
            start_time = datetime.now(UTC)

            # Build headers for HTTP/SSE clients if authentication is required
            headers = None
            if (
                temp_tool.requires_authentication
                and session.security_config
                and session.security_config.get("secret_value")
            ):
                # Extract secret value and authentication type from security config
                secret_value = session.security_config["secret_value"]
                auth_type = session.security_config.get("authentication_type", "api_key")

                # Format Authorization header based on authentication type
                if auth_type == "api_key":
                    # Elastic and most API key services use "ApiKey <key>" format
                    headers = {"Authorization": f"ApiKey {secret_value}"}
                elif auth_type == "oauth" or auth_type == "bearer":
                    headers = {"Authorization": f"Bearer {secret_value}"}
                elif auth_type == "basic":
                    # Basic auth expects base64-encoded "username:password"
                    headers = {"Authorization": f"Basic {secret_value}"}
                else:
                    # Custom or unknown type - pass through as-is
                    headers = {"Authorization": secret_value}

                logger.info(
                    f"Using {auth_type} authentication header for connection test of {temp_tool.tool_id}",
                    extra={
                        "tool_id": temp_tool.tool_id,
                        "auth_type": auth_type,
                        "endpoint": temp_tool.mcp_endpoint,
                    },
                )

            # Create client with authentication headers if needed
            client = self.discovery_service.create_mcp_client(temp_tool, headers=headers)

            await client.connect()
            server_capabilities = await client.initialize()
            tools_list = await client.list_tools()
            await client.disconnect()

            response_time_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Store results
            session.connection_result = {
                "tested": True,
                "success": True,
                "response_time_ms": response_time_ms,
                "server_capabilities": server_capabilities,
                "discovered_tools": tools_list,
                "tool_count": len(tools_list),
            }
            session.validation_errors.pop("connection_test", None)
            session.can_proceed = True

            logger.info(
                f"Connection test successful for session {session.session_id}: "
                f"{len(tools_list)} tools discovered"
            )

            return {
                "success": True,
                "response_time_ms": response_time_ms,
                "capabilities": server_capabilities,
                "tools": tools_list,
            }

        except Exception as e:
            error_msg = f"Connection test failed: {e!s}"
            session.connection_result = {
                "tested": True,
                "success": False,
                "error": str(e),
            }
            session.validation_errors["connection_test"] = [error_msg]
            session.can_proceed = False

            logger.error(f"Connection test failed for session {session.session_id}: {e}")

            return {
                "success": False,
                "error": error_msg,
            }

    async def _handle_security_config(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 4: Security Configuration.

        Validates security configuration and secret requirements.
        """
        try:
            security_data = SecurityConfigData(**data)
        except Exception as e:
            session.validation_errors["security_config"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        # Validate authentication requirements
        if security_data.requires_authentication and (
            not security_data.secret_name or not security_data.secret_value
        ):
            error_msg = "Authentication requires secret_name and secret_value"
            session.validation_errors["security_config"] = [error_msg]
            session.can_proceed = False
            return {"success": False, "error": error_msg}

        # Store validated data (secret_value will be encrypted during commit)
        session.security_config = security_data.model_dump()
        session.validation_errors.pop("security_config", None)
        session.can_proceed = True

        logger.info(f"Security config validated for session {session.session_id}")

        return {"success": True}

    async def _handle_permissions(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 5: Permissions & Limits.

        Validates permission configuration.
        """
        try:
            permissions_data = PermissionsData(**data)
        except Exception as e:
            session.validation_errors["permissions"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        # Store validated data
        session.permissions_config = permissions_data.model_dump()
        session.validation_errors.pop("permissions", None)
        session.can_proceed = True

        logger.info(f"Permissions validated for session {session.session_id}")

        return {"success": True}

    async def _handle_review(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle Phase 6: Review.

        Prepare summary for user review.
        """
        try:
            review_data = ReviewData(**data)
        except Exception as e:
            session.validation_errors["review"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        if review_data.action == "edit":
            # Allow going back to edit
            session.can_proceed = False
            return {
                "success": True,
                "action": "edit",
                "message": "Return to previous phases to edit configuration",
            }

        # Confirm ready for commit
        session.validation_errors.pop("review", None)
        session.can_proceed = True

        logger.info(f"Review confirmed for session {session.session_id}")

        return {
            "success": True,
            "action": "confirm",
            "message": "Ready to commit registration",
        }

    async def _handle_commit(
        self,
        session: RegistrationSession,
        data: dict[str, Any],
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Handle Phase 7: Commit.

        Atomically create tool with all configuration.
        """
        try:
            commit_data = CommitData(**data)
        except Exception as e:
            session.validation_errors["commit"] = [str(e)]
            session.can_proceed = False
            return {"success": False, "error": str(e)}

        if not commit_data.confirmed:
            return {
                "success": False,
                "error": "Confirmation required to commit registration",
            }

        # Begin atomic registration
        try:
            # Validate required phase data exists
            if not session.basic_info or not session.mcp_config:
                error_msg = "Basic info and MCP config required for commit"
                session.validation_errors["commit"] = [error_msg]
                session.can_proceed = False
                return {"success": False, "error": error_msg}

            # Build ToolCreate schema from collected data
            tool_create_data = {
                **session.basic_info,
                **session.mcp_config,
            }
            if session.security_config:
                tool_create_data.update(session.security_config)
            if session.permissions_config:
                tool_create_data.update(session.permissions_config)

            # Remove role_permissions for separate handling
            role_permissions = tool_create_data.pop("role_permissions", [])

            # Remove secret_value (handled separately)
            secret_value = tool_create_data.pop("secret_value", None)
            secret_expires_at = tool_create_data.pop("secret_expires_at", None)

            # Store discovered capabilities if available
            if session.connection_result and session.connection_result.get("success"):
                tool_create_data["capabilities"] = session.connection_result.get(
                    "server_capabilities"
                )
                # Extract parameters_schema from discovered tools if available
                discovered_tools = session.connection_result.get("discovered_tools", [])
                if discovered_tools:
                    # Use first tool's schema as example
                    tool_create_data["parameters_schema"] = discovered_tools[0].get(
                        "inputSchema", {}
                    )

            tool_create = ToolCreate(**tool_create_data)

            # Create tool record
            tool = await self.tool_service.create_tool(tool_create, user_id)

            # Create secret if provided
            if secret_value and tool_create.secret_name:
                await self.secrets_manager.store_secret(
                    tool_id=tool.id,
                    secret_name=tool_create.secret_name,
                    secret_type=tool_create.authentication_type or "api_key",
                    secret_value=secret_value,
                    expires_at=secret_expires_at,
                    created_by=user_id,
                )

            # Create permissions
            for perm in role_permissions:
                await self.permission_service.grant_permission(
                    tool_id=tool.id,
                    role=perm["role"],
                    can_view=perm.get("can_view", False),
                    can_use=perm.get("can_use", False),
                    can_configure=perm.get("can_configure", False),
                    max_calls_per_hour=perm.get("max_calls_per_hour"),
                    max_calls_per_day=perm.get("max_calls_per_day"),
                    created_by_user_id=user_id,
                )

            # Cleanup session
            del self._sessions[session.session_id]

            logger.info(
                f"Tool registration committed: {tool.tool_id} (UUID: {tool.id})",
                extra={"tool_id": tool.tool_id, "tool_uuid": str(tool.id)},
            )

            return {
                "success": True,
                "tool_id": tool.id,
                "tool_identifier": tool.tool_id,
                "message": f"Tool '{tool.name}' registered successfully",
            }

        except Exception as e:
            logger.error(f"Tool registration commit failed: {e}", exc_info=True)
            await self.db.rollback()

            session.validation_errors["commit"] = [str(e)]
            session.can_proceed = False

            return {
                "success": False,
                "error": f"Registration failed: {e!s}",
            }

    # Public API

    async def process_phase(
        self,
        session_id: str | None,
        phase: ToolRegistrationPhase,
        data: dict[str, Any],
        user_id: uuid.UUID,
    ) -> tuple[RegistrationSession, dict[str, Any]]:
        """
        Process a registration phase.

        Args:
            session_id: Existing session ID (None for first phase)
            phase: Current phase to process
            data: Phase-specific data
            user_id: User performing registration

        Returns:
            Tuple of (session, phase_result)
        """
        # Cleanup expired sessions periodically
        self._cleanup_expired_sessions()

        # Get or create session
        if session_id:
            try:
                session = self._get_session(session_id)
            except ValueError as e:
                # Session not found or expired
                # If this is BASIC_INFO phase, allow creating a new session
                # Otherwise, re-raise the error (user needs to start over)
                if phase == ToolRegistrationPhase.BASIC_INFO:
                    logger.warning(
                        f"Session {session_id} not found or expired, creating new session for BASIC_INFO phase"
                    )
                    session = self._create_session(user_id)
                else:
                    raise ValueError(
                        f"Registration session '{session_id}' not found or expired. "
                        "Please start the registration process from the beginning."
                    ) from e
        else:
            if phase != ToolRegistrationPhase.BASIC_INFO:
                raise ValueError("First phase must be BASIC_INFO")
            session = self._create_session(user_id)

        # Process phase
        if phase == ToolRegistrationPhase.BASIC_INFO:
            result = await self._handle_basic_info(session, data)
        elif phase == ToolRegistrationPhase.MCP_CONFIG:
            result = await self._handle_mcp_config(session, data)
        elif phase == ToolRegistrationPhase.CONNECTION_TEST:
            result = await self._handle_connection_test(session, data)
        elif phase == ToolRegistrationPhase.SECURITY_CONFIG:
            result = await self._handle_security_config(session, data)
        elif phase == ToolRegistrationPhase.PERMISSIONS:
            result = await self._handle_permissions(session, data)
        elif phase == ToolRegistrationPhase.REVIEW:
            result = await self._handle_review(session, data)
        elif phase == ToolRegistrationPhase.COMMIT:
            result = await self._handle_commit(session, data, user_id)
        else:
            raise ValueError(f"Unknown phase: {phase}")

        # Update session phase if successful
        if result.get("success") and session.can_proceed:
            next_phase = self._get_next_phase(phase)
            if next_phase:
                session.current_phase = next_phase

        self._update_session(session)

        return session, result

    def get_session_state(self, session_id: str) -> RegistrationSession:
        """Retrieve session state."""
        return self._get_session(session_id)

    def cancel_registration(self, session_id: str) -> None:
        """Cancel registration and cleanup session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Registration cancelled: {session_id}")
