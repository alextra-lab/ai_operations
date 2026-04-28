"""
Template Engine for Use Case Configuration and Prompt Management.

Extracted from OrchestratorController to follow Single Responsibility Principle.
Handles template selection, configuration loading, and prompt management.

Part of P4-F11 Layer 4 orchestrator refactoring.
"""

from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType
from ..schemas.use_case_config import UseCaseConfig
from ..services.use_case_config_loader import UseCaseConfigLoader

logger = configure_logging(service_name="template_engine", log_level="INFO", log_format="json")


class TemplateEngine:
    """
    Template Engine for use case configuration and prompt management.

    Responsibilities:
    - Load use case configurations by ID or intent type
    - Load multi-role prompts (system, developer, fewshots)
    - Validate configurations
    - Select appropriate templates for execution

    This engine separates template/config concerns from execution logic,
    enabling better testability and maintainability.
    """

    def __init__(self, db: AsyncSession, config_loader: UseCaseConfigLoader | None = None):
        """
        Initialize Template Engine.

        Args:
            db: Async database session for data access
            config_loader: Optional pre-configured UseCaseConfigLoader instance
        """
        self.db = db
        self.config_loader = config_loader or UseCaseConfigLoader(db)
        logger.info("TemplateEngine initialized")

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
                    logger.info("Loaded config for use_case_id: %s", use_case_id)
                    return config

            # Fall back to loading by intent type
            config = await self.config_loader.load_config_by_intent(request_type)
            if config:
                logger.info("Loaded config for intent_type: %s", request_type)
                return config

            # Use default config if no specific config found
            logger.info("No specific config found for %s, using default", request_type)
            return self.config_loader.get_default_config()

        except Exception as e:
            logger.warning("Error loading use case config: %s, using default", str(e))
            return self.config_loader.get_default_config()

    async def load_use_case_prompts(
        self, use_case_id: str | None = None, intent_type: RequestType | None = None
    ) -> dict[str, Any] | None:
        """
        Load use case prompts (multi-role) from use case metadata.

        Args:
            use_case_id: Optional specific use case ID to load
            intent_type: Optional intent type to match

        Returns:
            Dictionary with prompt data (system_prompt, developer_prompt, fewshots) or None
        """
        from sqlalchemy import select

        from ..db.models import UseCase as DBUseCase

        try:
            # ADR-070: is_active gates discovery, not execution.
            # Explicit use_case_id → load regardless of is_active (caller authorised).
            # Intent-type lookup → discovery, so only active use cases.
            if use_case_id:
                stmt = select(DBUseCase).where(DBUseCase.use_case_id == use_case_id)
            elif intent_type:
                stmt = select(DBUseCase).where(
                    DBUseCase.is_active.is_(True),
                    DBUseCase.intent_type == intent_type.value,
                )
            else:
                return None

            result = await self.db.execute(stmt)
            use_case = result.scalar_one_or_none()

            if not use_case or not use_case.metadata_json:
                return None

            prompts = use_case.metadata_json.get("prompts")
            if prompts:
                logger.info(
                    "Loaded multi-role prompts for use_case_id: %s",
                    use_case.use_case_id,
                )
                return cast("dict[str, Any] | None", prompts)

            return None

        except Exception as e:
            logger.warning("Error loading use case prompts: %s", str(e))
            return None

    async def select_template(
        self, request_type: RequestType, use_case_id: str | None = None
    ) -> tuple[UseCaseConfig, dict[str, Any] | None]:
        """
        Select and load complete template (config + prompts).

        This is the main entry point for template selection, combining
        configuration loading and prompt loading.

        Args:
            request_type: Detected request type
            use_case_id: Optional specific use case ID

        Returns:
            Tuple of (UseCaseConfig, prompts dict or None)
        """
        # Load configuration
        config = await self.load_use_case_config(request_type, use_case_id)

        # Load prompts (only if use_case_id is provided)
        prompts = None
        if use_case_id:
            prompts = await self.load_use_case_prompts(use_case_id)

        logger.info(
            "Template selected: request_type=%s, has_prompts=%s",
            request_type,
            prompts is not None,
        )

        return config, prompts
