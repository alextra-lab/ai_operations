"""
Orchestrator Controller for AI Operations Platform.

This module implements the main Orchestrator class that integrates all components
and manages the complete request-response flow. It provides a single entry point
for processing requests, handling authentication, intent parsing, prompt assembly,
LLM routing, and response formatting.

The Orchestrator is the core component that coordinates the workflow:
Authentication → Intent Parser → LLM-Guard → Retrieval Engine → Prompt Assembler → LLM Router → Response Formatter
"""

import os
import time
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType
from ..schemas.response import FormattedResponse
from ..schemas.use_case_config import UseCaseConfig
from ..services.async_history_service import AsyncHistoryService
from ..services.telemetry_integration_service import TelemetryIntegration
from ..services.token_tracker import TokenTracker
from ..services.use_case_config_loader import UseCaseConfigLoader
from ..utils.auth import jwt_validator
from .intent_parser import IntentParser
from .llm_router import LLMRouter
from .prompt_assembler import PromptAssembler
from .response_formatter import ResponseFormatter
from .tool_validator import ToolValidator

logger = configure_logging(
    service_name="orchestrator_controller", log_level="INFO", log_format="json"
)


class Orchestrator:
    """
    Main orchestrator class that integrates all components and manages the request-response flow.

    This class provides a single entry point for processing requests, handling:
    1. Authentication verification
    2. Intent parsing
    3. LLM-Guard validation
    4. Retrieval for context
    5. Prompt assembly
    6. LLM request routing
    7. Response formatting

    It serves as the central coordination point for the entire system, ensuring
    that all components work together seamlessly.
    """

    def __init__(
        self,
        async_db: AsyncSession,
        config: dict[str, Any] | None = None,
        intent_parser: IntentParser | None = None,
        prompt_assembler: PromptAssembler | None = None,
        llm_router: LLMRouter | None = None,
        response_formatter: ResponseFormatter | None = None,
        config_loader: UseCaseConfigLoader | None = None,
    ):
        """
        Initialize the Orchestrator with all required components.

        Args:
            async_db: Async database session (required for all services)
            config: Optional configuration dictionary
            intent_parser: Optional pre-configured IntentParser instance
            prompt_assembler: Optional pre-configured PromptAssembler instance
            llm_router: Optional pre-configured LLMRouter instance
            response_formatter: Optional pre-configured ResponseFormatter instance
            config_loader: Optional pre-configured UseCaseConfigLoader instance

        Raises:
            ValueError: If prompt_assembler is None and async_db is None

        Note:
            - All services now use async_db (UseCaseConfigLoader, TelemetryIntegration,
              AsyncHistoryService, and TokenTracker).
            - `async_db` is required for PromptAssembler and all other services.
              Either provide `async_db` or pass pre-configured instances.
        """
        self.async_db = async_db
        self.config = config or {}

        # Set up LLM-Guard client configuration
        # Service name in docker-compose.yml is 'llm-guard-svc'
        self.llm_guard_url = self.config.get("llm_guard_url", "http://llm-guard-svc:8081")
        self.llm_guard_timeout = self.config.get("llm_guard_timeout", 10.0)

        # Initialize components (use provided instances or create new ones)
        self.intent_parser = intent_parser or IntentParser(
            config=self.config.get("intent_parser_config")
        )

        # Use async_db for PromptAssembler if available
        # (Note: PromptAssembler now requires AsyncSession)
        if prompt_assembler is None:
            if async_db is not None:
                self.prompt_assembler = PromptAssembler(async_db)
            else:
                raise ValueError(
                    "PromptAssembler requires AsyncSession. "
                    "Please provide async_db parameter or pass prompt_assembler instance."
                )
        else:
            self.prompt_assembler = prompt_assembler

        # Initialize telemetry integration for Stateless Core v1
        self.telemetry_integration = TelemetryIntegration(async_db)

        if llm_router is not None:
            self.llm_router = llm_router
        else:
            gateway_url = self.config.get("inference_gateway_url")
            user_token = self.config.get("user_jwt_token")
            self.llm_router = LLMRouter(
                gateway_url=gateway_url,
                max_retries=self.config.get("max_retries", 3),
                user_jwt_token=user_token,
                request_timeout_seconds=self.config.get("request_timeout_seconds"),
            )

        self.response_formatter = response_formatter or ResponseFormatter(
            confidence_threshold=self.config.get("confidence_threshold", 0.7),
            enable_suggested_actions=self.config.get("enable_suggested_actions", True),
        )

        # Initialize use case config loader
        self.config_loader = config_loader or UseCaseConfigLoader(async_db)

        # Initialize enterprise services
        self.history_service = AsyncHistoryService(async_db)
        self.token_tracker = TokenTracker(async_db)
        self.tool_validator = ToolValidator()

        logger.info("Orchestrator initialized with all components")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Orchestrator.__init__ completed successfully during test.")

    async def load_use_case_config(
        self, request_type: RequestType, use_case_id: str | None = None
    ) -> UseCaseConfig:
        """
        Load use case configuration for the given request type or use case ID.

        Args:
            request_type: The detected request type
            use_case_id: Optional specific use case ID to load

        Returns:
            UseCaseConfig instance or default config if not found
        """
        try:
            # Try to load by specific use case ID first if provided
            if use_case_id:
                config = await self.config_loader.load_config(use_case_id)
                if config:
                    logger.info(f"Loaded config for use_case_id: {use_case_id}")
                    return config

            # Fall back to loading by intent type
            config = await self.config_loader.load_config_by_intent(request_type)
            if config:
                logger.info(f"Loaded config for intent_type: {request_type}")
                return config

            # Use default config if no specific config found
            logger.info(f"No specific config found for {request_type}, using default")
            return self.config_loader.get_default_config()

        except Exception as e:
            logger.warning(f"Error loading use case config: {e!s}, using default")
            return self.config_loader.get_default_config()

    async def load_use_case_prompts(self, use_case_uuid: str) -> dict[str, Any] | None:
        """
        Load use case prompts (multi-role) from use case metadata.

        REQUIRES a specific use_case_uuid. This function should only be called
        when executing a specific use case, not for generic conversations.

        Args:
            use_case_uuid: UUID of the use case to load (REQUIRED) - this is the `id` column, not `use_case_id`

        Returns:
            Dictionary with prompt data (system_prompt, developer_prompt, fewshots) or None if not found
        """
        from uuid import UUID

        from sqlalchemy import select

        from ..db.models import UseCase as DBUseCase

        try:
            # Convert string UUID to UUID object
            uc_uuid = UUID(use_case_uuid) if isinstance(use_case_uuid, str) else use_case_uuid

            # ADR-070: is_active gates discovery, not execution.
            # When loading by explicit UUID the caller has already authorised access.
            stmt = select(DBUseCase).where(DBUseCase.id == uc_uuid)
            result = await self.async_db.execute(stmt)
            use_case = result.scalar_one_or_none()

            if not use_case or not use_case.metadata_json:
                logger.warning("Use case UUID %s not found or has no metadata", use_case_uuid)
                return None

            prompts = use_case.metadata_json.get("prompts")
            if prompts:
                logger.info(
                    "Loaded multi-role prompts for use case: %s (UUID: %s)",
                    use_case.use_case_id,
                    use_case_uuid,
                )
                data: dict[str, Any] = prompts
                return data

            logger.warning(
                "Use case %s (UUID: %s) has no prompts in metadata",
                use_case.use_case_id,
                use_case_uuid,
            )
            return None

        except Exception as e:
            logger.warning(
                "Error loading use case prompts for UUID %s: %s",
                use_case_uuid,
                type(e).__name__,
            )
            return None

    def _validate_tool_allowlist(self, use_case_config: UseCaseConfig) -> None:
        """
        Validate and log tool allowlist configuration.

        This is a placeholder for future MCP integration. Currently logs
        warnings if tools are specified in the allowlist, as tool calling
        is not yet implemented.

        Args:
            use_case_config: Use case configuration to validate
        """
        if not use_case_config.tools_allowlist:
            logger.debug("No tool allowlist configured, all tools permitted")
            return

        logger.info("Tool allowlist configured: %s", use_case_config.tools_allowlist)

        # Log warning about future implementation
        logger.warning(
            "Tool calling is not yet implemented. "
            "Configured tools (%d) "
            "will be validated when MCP integration is available.",
            len(use_case_config.tools_allowlist),
        )

        # Future: Validate that requested tools are in allowlist
        # For now, just validate that the allowlist format is correct
        for tool_name in use_case_config.tools_allowlist:
            if not isinstance(tool_name, str) or not tool_name.strip():
                logger.error("Invalid tool name in allowlist: %r", tool_name)
                raise ValueError(f"Tool allowlist contains invalid tool name: {tool_name!r}")

    async def verify_authentication(self, token: str) -> dict[str, Any]:
        """
        Verify the authentication token and user authorization.

        Args:
            token: JWT token to verify

        Returns:
            Dictionary containing user information from the token

        Raises:
            HTTPException: If token is invalid or user is not authorized
        """
        if not token:
            logger.warning("Authentication failed: No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Token is required.",
            )

        # Verify the token using the JWT module
        payload = jwt_validator.verify_token(token)
        if not payload:
            logger.warning("Authentication failed: Invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Authentication failed: Token missing user ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format: missing user ID",
            )

        # Check user role if required
        if self.config.get("check_user_role", True):
            user_role = payload.get("role", "user")
            required_role = self.config.get("required_role", "user")

            if user_role not in ["admin", required_role]:
                logger.warning(
                    f"Authorization failed: User {user_id} with role {user_role} not authorized"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized. Required role: {required_role}",
                )

        logger.info(f"Authentication successful for user: {user_id}")
        return cast("dict[str, Any]", payload)

    async def validate_with_llm_guard(
        self,
        input_text: str,
        user_id: str | None = None,
        request_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, float, bool, dict[str, Any]]:
        """
        Validate the input text using the LLM-Guard service with graceful degradation.

        Args:
            input_text: The input text to validate
            user_id: Optional user ID for tracking
            request_id: Optional request ID for tracking
            context: Optional context information for validation

        Returns:
            Tuple containing:
            - Sanitized text (or original if no issues)
            - Risk score (0-1, higher is riskier)
            - Boolean indicating if the text was modified
            - Dictionary with detailed validation results

        Note:
            This method implements graceful degradation. If LLM-Guard service is unavailable
            or disabled, it returns the original input with safe defaults rather than failing
            the entire request.
        """
        # Check if LLM-Guard is disabled via configuration. Disabled by default
        # (LLG-04 finale): native scanners need models staged manually first.
        llm_guard_enabled = self.config.get("llm_guard_enabled", False)
        if not llm_guard_enabled:
            logger.info("LLM-Guard validation disabled via configuration")
            return (
                input_text,
                0.0,
                False,
                {"status": "disabled", "message": "LLM-Guard validation is disabled"},
            )

        logger.info(f"Validating input with LLM-Guard, length: {len(input_text)}")

        try:
            # Prepare the request to LLM-Guard
            headers = {"Content-Type": "application/json"}

            # Add tracking headers if available
            if user_id:
                headers["X-User-ID"] = user_id
            if request_id:
                headers["X-Request-ID"] = request_id

            # Prepare the request body
            llm_guard_context = context or {
                "source": "orchestrator",
                "timestamp": datetime.now(UTC),
            }
            # Ensure all values in the context are strings for LLM-Guard
            stringified_llm_guard_context = {k: str(v) for k, v in llm_guard_context.items()}

            validation_request = {
                "input_text": input_text,
                "strict_mode": self.config.get("llm_guard_strict_mode", False),
                "context": stringified_llm_guard_context,  # Use the stringified version
            }

            # Make the API call to LLM-Guard
            async with httpx.AsyncClient(timeout=self.llm_guard_timeout) as client:
                response = await client.post(
                    f"{self.llm_guard_url}/api/validate",
                    json=validation_request,
                    headers=headers,
                )

                # Check for successful response
                response.raise_for_status()
                result = response.json()

                sanitized_text = result.get("sanitized_text", input_text)
                risk_score = result.get("risk_score", 0.0)
                modified = result.get("modified", False)
                details = result.get("details", {})

                # Log the validation results
                logger.info(f"LLM-Guard validation: risk_score={risk_score}, modified={modified}")
                if modified:
                    logger.info("Input was modified by LLM-Guard")

                return sanitized_text, risk_score, modified, details

        except httpx.HTTPStatusError as e:
            logger.warning(
                f"LLM-Guard validation HTTP error: {e!s} - proceeding without validation"
            )
            return (
                input_text,
                0.0,
                False,
                {
                    "status": "error",
                    "error_type": "http_error",
                    "message": f"LLM-Guard service returned HTTP error: {e!s}",
                    "graceful_degradation": True,
                },
            )
        except httpx.RequestError as e:
            logger.warning(f"LLM-Guard request error: {e!s} - proceeding without validation")
            return (
                input_text,
                0.0,
                False,
                {
                    "status": "error",
                    "error_type": "connection_error",
                    "message": f"LLM-Guard service unavailable: {e!s}",
                    "graceful_degradation": True,
                },
            )
        except Exception as e:
            logger.warning(f"LLM-Guard unexpected error: {e!s} - proceeding without validation")
            return (
                input_text,
                0.0,
                False,
                {
                    "status": "error",
                    "error_type": "unexpected_error",
                    "message": f"LLM-Guard validation failed: {e!s}",
                    "graceful_degradation": True,
                },
            )

    def _extract_search_query(self, query: str) -> str:
        """
        Extract the actual search query from structured input.

        If the query contains field labels (e.g., "incident_details: What is IAL?"),
        extract just the meaningful text values for semantic search.

        Args:
            query: The raw query string (may contain field labels)

        Returns:
            Extracted search query text
        """
        # Check if query contains field labels (format: "field_name: value")
        if ":" in query and "\n" in query:
            # Extract values from structured fields
            lines = query.strip().split("\n")
            values = []
            for line in lines:
                if ":" in line:
                    # Extract the value after the colon
                    _, value = line.split(":", 1)
                    value = value.strip()
                    if value and len(value) > 3:  # Only include substantial values
                        values.append(value)

            if values:
                # Combine all extracted values
                extracted = " ".join(values)
                logger.info(
                    "Extracted search query from structured input, length=%d",
                    len(extracted),
                )
                return extracted

        # If no structured format detected, return the original query
        return query

    async def retrieve_context(
        self,
        query: str,
        intent_type: RequestType,
        request_id: str | None = None,
        token: str | None = None,
        use_case_config: UseCaseConfig | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve relevant context for the query using the retrieval service.

        Args:
            query: The user's query (may contain structured fields)
            intent_type: The type of request
            request_id: Optional request ID for tracking
            token: Optional JWT token for authentication
            use_case_config: Optional use case configuration

        Returns:
            Dictionary containing retrieved context with sources and metadata
        """
        logger.info(f"Retrieving context for query (intent: {intent_type})")

        # Extract the actual search query from structured input
        search_query = self._extract_search_query(query)

        # Check if RAG is enabled in use case config
        if use_case_config and not use_case_config.rag.enabled:
            logger.info("RAG disabled in use case config, skipping context retrieval")
            return {
                "sources": [],
                "metadata": {
                    "retrieval_time": 0.0,
                    "total_sources": 0,
                    "rag_enabled": False,
                },
            }

        retrieval_start_time = time.time()

        try:
            # Get retrieval service URL from config or environment
            retrieval_svc_url = self.config.get(
                "retrieval_svc_url",
                "http://corpus-service:8001/api/v1",
            )

            # Use top_k from use case config if available, otherwise fall back to intent-based logic
            if use_case_config:
                top_k = use_case_config.rag.top_k
                similarity_threshold = use_case_config.rag.similarity_threshold
                logger.info(
                    f"Using config values: top_k={top_k}, similarity_threshold={similarity_threshold}"
                )
            else:
                top_k = self._get_top_k_for_intent(intent_type)
                similarity_threshold = self.config.get("min_relevancy_score", 0.3)
                logger.info(
                    f"Using default values: top_k={top_k}, similarity_threshold={similarity_threshold}"
                )

            # Prepare request to retrieval service
            retrieval_request = {
                "query_text": search_query,  # Use extracted search query
                "top_k": top_k,
                "min_relevancy_score": similarity_threshold,
                "run_id": request_id,  # Pass the request_id as run_id for usage tracking
            }

            # NOTE: Embedding model no longer in Use Case config
            # Retrieval service will determine embedding model from collection(s)
            # System uses DEFAULT_EMBEDDING_MODEL from environment

            # Add metadata filters if specified in use case config
            if use_case_config and use_case_config.rag and use_case_config.rag.metadata_filters:
                filters = []
                for field, value in use_case_config.rag.metadata_filters.items():
                    filters.append({"field": field, "value": value})
                retrieval_request["filters"] = filters
                logger.info(
                    f"Using metadata filters from config: {use_case_config.rag.metadata_filters}"
                )

            # Make request to retrieval service
            timeout = self.config.get("retrieval_timeout", 10.0)
            url = f"{retrieval_svc_url}/query/semantic-search"

            # Add request_id to headers for tracking
            headers = {"Content-Type": "application/json"}
            if request_id:
                headers["X-Request-ID"] = request_id
            if token:
                headers["Authorization"] = f"Bearer {token}"

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=retrieval_request, headers=headers)
                response.raise_for_status()
                search_results = response.json()

            # Transform results into expected context format
            sources = []
            for result in search_results.get("results", []):
                source = {
                    "document_id": result.get("document_id"),
                    "title": result.get("document_title", "Unknown Document"),
                    "content": result.get("text_snippet", ""),
                    "relevance_score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                }
                sources.append(source)

            retrieval_time = time.time() - retrieval_start_time

            context = {
                "sources": sources,
                "metadata": {
                    "retrieval_time": retrieval_time,
                    "intent_type": intent_type.value,
                    "query": query,
                    "sources_found": len(sources),
                    "retrieval_method": "semantic_search",
                },
            }

            logger.info(
                f"Retrieved {len(sources)} sources for query in {retrieval_time:.3f}s "
                f"(intent: {intent_type})"
            )

            return context

        except httpx.HTTPStatusError as e:
            logger.error(f"Retrieval service HTTP error: {e!s}")
            # Return empty context with error info for graceful degradation
            return self._get_fallback_context(query, intent_type, f"HTTP error: {e!s}")

        except httpx.RequestError as e:
            logger.error(f"Retrieval service request error: {e!s}")
            return self._get_fallback_context(query, intent_type, f"Request error: {e!s}")

        except Exception as e:
            logger.error(f"Unexpected error during context retrieval: {e!s}")
            return self._get_fallback_context(query, intent_type, f"Unexpected error: {e!s}")

    def _determine_streaming_behavior(
        self,
        explicit_stream: bool,
        use_case_config: "UseCaseConfig",
        intent_type: RequestType,
    ) -> bool:
        """
        Determine streaming behavior based on precedence rules.

        Precedence order:
        1. Request flag (explicit stream parameter) - highest priority
        2. Template default (config.policy.streaming_default) - medium priority
        3. Intent default (SUMMARIZATION defaults to streaming=True) - lower priority
        4. Global default (stream=False) - lowest priority

        Args:
            explicit_stream: Explicit stream parameter from request
            use_case_config: Use case configuration containing policy settings
            intent_type: Detected intent type

        Returns:
            Final streaming decision (True/False)
        """
        # Priority 1: Explicit request flag overrides everything
        if explicit_stream is not None:
            logger.debug(f"Using explicit stream flag: {explicit_stream}")
            return explicit_stream
        # Priority 2: Template default from config (only if explicitly set)
        if (
            hasattr(use_case_config, "policy")
            and hasattr(use_case_config.policy, "streaming_default")
            and use_case_config.policy.model_fields_set
            and "streaming_default" in use_case_config.policy.model_fields_set
        ):
            template_default = use_case_config.policy.streaming_default
            logger.debug(f"Using template streaming default: {template_default}")
            return template_default

        # Priority 3: Intent-specific defaults
        if intent_type == RequestType.SUMMARIZATION:
            logger.debug("SUMMARIZATION intent defaults to streaming=True")
            return True

        # Priority 4: Global default
        logger.debug("Using global default: streaming=False")
        return False

    def _get_top_k_for_intent(self, intent_type: RequestType) -> int:
        """
        Determine the number of sources to retrieve based on intent type.

        Args:
            intent_type: The request intent type

        Returns:
            Number of sources to retrieve
        """
        intent_to_top_k = {
            RequestType.QUERY: 5,
            RequestType.SUMMARIZATION: 8,
            RequestType.ENRICHMENT: 3,
            RequestType.RULE_GENERATION: 4,
        }
        return intent_to_top_k.get(intent_type, 5)

    def _get_fallback_context(
        self, query: str, intent_type: RequestType, error_msg: str
    ) -> dict[str, Any]:
        """
        Create fallback context when retrieval fails.

        Args:
            query: The original query
            intent_type: The request intent type
            error_msg: Error message to include

        Returns:
            Fallback context dictionary
        """
        return {
            "sources": [],
            "metadata": {
                "retrieval_time": 0.0,
                "intent_type": intent_type.value,
                "query": query,
                "sources_found": 0,
                "retrieval_method": "fallback",
                "error": error_msg,
            },
        }

    # =========================================================================
    # LEGACY METHODS REMOVED (October 25, 2025)
    # =========================================================================
    # The following methods have been removed (1,037 lines deleted):
    #   - process() - Legacy orchestration method (731 lines)
    #   - _process_stream() - Legacy streaming support (203 lines)
    #   - _record_streaming_metrics() - Legacy metrics (103 lines)
    #
    # Replaced by Pipeline+Steps architecture (ADR-036):
    #   - UseCaseRunner + 6 Pipeline Steps
    #   - See: orchestrator/runner.py, orchestrator/steps/*.py
    # =========================================================================

    async def record_retrieval(
        self,
        document_id: str | None,
        chunk_ids: list[str],
        user_id: str | None,
        query_text: str,
        relevancy_scores: list[float],
        metadata: dict[str, Any],
        run_id: str,
        rag_confidence: float | None = None,
        total_results_found: int | None = None,
        source_document_count: int | None = None,
        average_relevancy: float | None = None,
    ) -> None:
        """
        Record a retrieval event by calling the retrieval service.
        """
        try:
            retrieval_svc_url = self.config.get(
                "retrieval_svc_url",
                "http://corpus-service:8001/api/v1",
            )
            url = f"{retrieval_svc_url}/usage/"

            headers = {"Content-Type": "application/json"}
            # The token is not needed here as the retrieval service is not expecting it for this endpoint.

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "document_id": document_id,
                        "chunk_ids": chunk_ids,
                        "user_id": user_id,
                        "query_text": query_text,
                        "relevancy_scores": relevancy_scores,
                        "metadata": metadata,
                        "run_id": run_id,
                        "rag_confidence": rag_confidence,
                        "total_results_found": total_results_found,
                        "source_document_count": source_document_count,
                        "average_relevancy": average_relevancy,
                    },
                    headers=headers,
                )
                response.raise_for_status()
            logger.info("Successfully recorded retrieval for run_id: %s", run_id)
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to record retrieval for run_id %s: %s",
                run_id,
                type(e).__name__,
            )
        except Exception as e:
            logger.error(
                "Unexpected error recording retrieval for run_id %s: %s",
                run_id,
                type(e).__name__,
            )

    def _is_guard_enabled(self) -> bool:
        """
        Check if LLM-Guard validation is enabled.

        Returns:
            True if guard should be used, False if disabled
        """
        enabled = bool(self.config.get("llm_guard_enabled", False))

        if not enabled:
            logger.info("LLM-Guard is disabled via configuration")

        return enabled

    def _should_retrieve_context(
        self,
        intent_response: Any = None,  # noqa: ARG002
        request_type: RequestType | None = None,  # noqa: ARG002
    ) -> bool:
        """
        Determine if context retrieval is needed for this request.

        Some request types don't benefit from retrieval (greetings, clarifications).
        Others explicitly require it (RAG queries, document searches).

        Args:
            intent_response: Parsed intent from intent parser (unused for now)
            request_type: Optional explicit request type (unused for now)

        Returns:
            True if retrieval should be attempted, False otherwise
        """
        # Check configuration
        retrieval_enabled = bool(self.config.get("retrieval_enabled", True))

        if not retrieval_enabled:
            logger.info("Retrieval is disabled via configuration")
            return False

        # For now, always attempt retrieval unless explicitly disabled
        # Future: Add more sophisticated logic based on intent_response and request_type
        return True

    def _collect_retrieval_metrics(
        self,
        context: dict[str, Any] | None,
        attempted: bool = True,
    ) -> dict[str, Any]:
        """
        Collect retrieval metrics from the context.

        ALWAYS returns a complete metrics dictionary. When retrieval is not
        attempted or fails, returns safe default values.

        Args:
            context: Context dictionary containing retrieval data (may be None)
            attempted: Whether retrieval was attempted

        Returns:
            Dict with retrieval metrics (always complete, never None)
        """
        if not attempted:
            return {
                "top_k": 0,
                "hits": 0,
                "similarity_scores": [],
                "source_count": 0,
                "status": "not_attempted",
                "reason": "retrieval_disabled_or_not_needed",
            }

        if not context:
            return {
                "top_k": 0,
                "hits": 0,
                "similarity_scores": [],
                "source_count": 0,
                "status": "failed",
                "reason": "no_context_provided",
            }

        sources = context.get("sources", [])
        if not sources:
            return {
                "top_k": context.get("top_k", 0),
                "hits": 0,
                "similarity_scores": [],
                "source_count": 0,
                "status": "no_results",
                "reason": "no_sources_found",
            }

        # Extract similarity scores from sources
        similarity_scores = []
        for source in sources:
            if isinstance(source, dict) and "relevance_score" in source:
                similarity_scores.append(source["relevance_score"])

        return {
            "top_k": context.get("top_k", 10),
            "hits": len(sources),
            "similarity_scores": similarity_scores,
            "source_count": len(
                {source.get("document_id") for source in sources if isinstance(source, dict)}
            ),
            "status": "completed",
        }

    def _collect_guard_metrics(
        self,
        input_text: str,
        risk_score: float,
        modified: bool,
        guard_details: dict[str, Any],
        attempted: bool = True,
    ) -> dict[str, Any]:
        """
        Collect LLM-Guard validation metrics.

        ALWAYS returns a complete metrics dictionary. When guard is disabled
        or fails, returns safe default values.

        Args:
            input_text: Original input text
            risk_score: Risk score from LLM-Guard
            modified: Whether input was modified
            guard_details: Detailed guard results
            attempted: Whether guard validation was attempted

        Returns:
            Dict with guard metrics (always complete, never None)
        """
        if not attempted:
            return {
                "risk_score": 0.0,
                "modified": False,
                "details": {
                    "status": "not_performed",
                    "reason": "guard_disabled",
                    "message": "LLM-Guard validation is disabled",
                },
                "input_length": len(input_text),
            }

        return {
            "risk_score": risk_score,
            "modified": modified,
            "details": guard_details or {"status": "completed", "scanners_run": []},
            "input_length": len(input_text),
        }

    def _create_error_response(self, error_msg: str, req_id: str) -> FormattedResponse:
        """
        Create a standardized error response.

        Args:
            error_msg: Error message to include
            req_id: Request ID for tracing

        Returns:
            FormattedResponse with error information
        """
        # Create error response with default metrics
        from ..schemas.response import (
            ConsolidatedMetrics,
            GuardMetrics,
            ModelMetrics,
            RetrievalMetrics,
            ServiceStatus,
        )

        error_metrics = ConsolidatedMetrics(
            retrieval=RetrievalMetrics(
                top_k=0,
                hits=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                source_count=0,
            ),
            guard=GuardMetrics(
                risk_score=0.0,
                modified=False,
                details={"status": "error", "message": error_msg},
            ),
            model=ModelMetrics(
                model_id="error",
                tokens_in=0,
                tokens_out=0,
                total_tokens=0,
                processing_time=0.0,
                metadata={"status": "error", "error": error_msg},
            ),
            confidence_score=0.0,
            service_status=ServiceStatus(
                retrieval_active=False,
                guard_active=False,
                model_active=False,
                embedding_active=False,
                retrieval_healthy=False,
                guard_healthy=False,
                model_healthy=False,
            ),
        )

        return FormattedResponse(
            response=f"An error occurred: {error_msg}",
            sources=[],
            confidence=0.0,
            metrics=error_metrics,
            suggested_actions={
                "retry": {
                    "label": "Retry Request",
                    "reason": "The previous request encountered an error.",
                }
            },
            request_id=req_id,
            cache_stats=None,
        )
