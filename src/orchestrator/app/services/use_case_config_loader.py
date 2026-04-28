"""
Use Case Config Loader Service for AI Operations Platform.

This service provides functionality to load and cache use case configurations
from the database, enabling template-driven behavior across the orchestrator system.

The UseCaseConfigLoader service handles:
- Loading configurations by use_case_id
- Loading configurations by intent_type (RequestType)
- In-memory caching with invalidation
- Database session management
- Error handling and fallbacks

This service is used by the orchestrator to apply use-case-specific configurations
to all downstream components during request processing.

P5-A23 Phase 7: Converted to async database patterns (Nov 2025).
"""

from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import get_logger

from ..db.models import UseCase
from ..schemas.intent import RequestType
from ..schemas.use_case_config import UseCaseConfig

logger = get_logger(__name__)

# Process-wide cache so that config updates (e.g. model change) are visible to
# the next execute without requiring a new process. Invalidated on use case update.
_config_cache_by_uuid: dict[str, UseCaseConfig] = {}


def invalidate_config_cache_for_use_case(use_case_id: str) -> None:
    """
    Invalidate cached config for a use case (e.g. after PATCH /use-cases/{id}).

    Call this from the use case update endpoint so the next execution
    loads the updated config (e.g. model selection) from the database.
    """
    if use_case_id in _config_cache_by_uuid:
        del _config_cache_by_uuid[use_case_id]
        logger.debug("Invalidated config cache for use case: %s", use_case_id)


class UseCaseConfigLoader:
    """
    Service for loading and caching use case configurations.

    This service provides methods to load use case configurations from the database
    with in-memory caching for performance. It supports loading by use_case_id
    or by intent_type, with automatic cache invalidation on updates.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the config loader with a database session.

        Args:
            db_session: SQLAlchemy async database session
        """
        self.db_session = db_session
        self._cache: dict[str, UseCaseConfig] = {}
        self._cache_by_intent: dict[str, UseCaseConfig] = {}

    async def load_config(self, use_case_uuid: str) -> UseCaseConfig | None:
        """
        Load use case configuration by UUID.

        Args:
            use_case_uuid: The UUID (id column) of the use case to load

        Returns:
            UseCaseConfig instance if found, None otherwise

        Raises:
            ValueError: If use_case_uuid is empty or None
            Exception: If database error occurs
        """
        if not use_case_uuid:
            raise ValueError("use_case_uuid cannot be empty or None")

        # Check process-wide cache first (invalidated on use case update)
        if use_case_uuid in _config_cache_by_uuid:
            logger.debug("Config cache hit for UUID: %s", use_case_uuid)
            return _config_cache_by_uuid[use_case_uuid]

        # Then instance cache
        if use_case_uuid in self._cache:
            logger.debug("Config cache hit for UUID: %s", use_case_uuid)
            return self._cache[use_case_uuid]

        try:
            from uuid import UUID

            # Convert to UUID object
            uc_uuid = UUID(use_case_uuid) if isinstance(use_case_uuid, str) else use_case_uuid

            # Query database for use case by UUID (id column).
            # ADR-070: is_active gates discovery, not execution.
            # When loading by explicit UUID the caller has already authorised
            # access (RBAC / draft ownership), so we do not filter by is_active.
            stmt = select(UseCase).where(UseCase.id == uc_uuid)
            result = await self.db_session.execute(stmt)
            use_case = result.scalar_one_or_none()

            if not use_case:
                logger.warning("Use case UUID not found: %s", use_case_uuid)
                return None

            if not use_case.config_json:
                logger.warning("Use case UUID %s has no config_json", use_case_uuid)
                return None

            # Parse and validate configuration
            config = UseCaseConfig.from_dict(use_case.config_json)

            # Cache the configuration (process-wide and instance)
            _config_cache_by_uuid[use_case_uuid] = config
            self._cache[use_case_uuid] = config

            logger.info(
                "Loaded config for use case: %s (UUID: %s)",
                use_case.use_case_id,
                use_case_uuid,
            )
            return config

        except Exception as e:
            logger.error("Error loading config for UUID %s: %s", use_case_uuid, str(e))
            raise

    async def load_config_by_intent(self, intent_type: RequestType) -> UseCaseConfig | None:
        """
        Load use case configuration by intent type.

        This method finds the first active use case that matches the intent_type
        and returns its configuration. This is useful when the specific use case
        is not known but the intent type is.

        Args:
            intent_type: The request type/intent to match

        Returns:
            UseCaseConfig instance if found, None otherwise

        Raises:
            ValueError: If intent_type is None
            Exception: If database error occurs
        """
        if not intent_type:
            raise ValueError("intent_type cannot be None")

        # Check cache first
        intent_key = intent_type.value
        if intent_key in self._cache_by_intent:
            logger.debug("Config cache hit for intent_type: %s", intent_type)
            return self._cache_by_intent[intent_key]

        try:
            # Query database for use case with matching intent_type
            stmt = select(UseCase).where(
                and_(
                    UseCase.intent_type == intent_type.value,
                    UseCase.is_active,
                )
            )
            result = await self.db_session.execute(stmt)
            use_case = result.scalar_one_or_none()

            if not use_case:
                logger.warning("No active use case found for intent_type: %s", intent_type)
                return None

            if not use_case.config_json:
                logger.warning("Use case has no config_json for intent_type: %s", intent_type)
                return None

            # Parse and validate configuration
            config = UseCaseConfig.from_dict(use_case.config_json)

            # Cache the configuration
            self._cache_by_intent[intent_key] = config

            logger.info(
                "Loaded config for intent_type: %s (use_case_id: %s)",
                intent_type,
                use_case.use_case_id,
            )
            return config

        except Exception as e:
            logger.error("Error loading config for intent_type %s: %s", intent_type, str(e))
            raise

    def get_default_config(self) -> UseCaseConfig:
        """
        Get the default configuration.

        This method returns a default UseCaseConfig instance when no specific
        configuration is found or when fallback behavior is needed.

        Returns:
            Default UseCaseConfig instance
        """
        logger.debug("Returning default configuration")
        return UseCaseConfig.get_default_config()

    def invalidate_cache(
        self, use_case_id: str | None = None, intent_type: RequestType | None = None
    ) -> None:
        """
        Invalidate cached configurations.

        This method clears the cache for specific configurations or all configurations.
        It should be called when use case configurations are updated in the database.

        Args:
            use_case_id: Specific use case ID to invalidate (None for all)
            intent_type: Specific intent type to invalidate (None for all)
        """
        if use_case_id:
            invalidate_config_cache_for_use_case(use_case_id)
            if use_case_id in self._cache:
                del self._cache[use_case_id]
                logger.debug("Invalidated cache for use_case_id: %s", use_case_id)
        else:
            _config_cache_by_uuid.clear()
            self._cache.clear()
            logger.debug("Invalidated all use_case_id cache")

        if intent_type:
            intent_key = intent_type.value
            if intent_key in self._cache_by_intent:
                del self._cache_by_intent[intent_key]
                logger.debug("Invalidated cache for intent_type: %s", intent_type)
        else:
            self._cache_by_intent.clear()
            logger.debug("Invalidated all intent_type cache")

    def clear_cache(self) -> None:
        """
        Clear all cached configurations.

        This method clears both the use_case_id and intent_type caches.
        It should be called when the service is being shut down or when
        a complete cache refresh is needed.
        """
        _config_cache_by_uuid.clear()
        self._cache.clear()
        self._cache_by_intent.clear()
        logger.debug("Cleared all configuration caches")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        return {
            "use_case_cache_size": len(self._cache),
            "intent_cache_size": len(self._cache_by_intent),
            "total_cached_configs": len(self._cache) + len(self._cache_by_intent),
        }

    async def preload_configs(
        self, use_case_ids: list[str] | None = None, intent_types: list[RequestType] | None = None
    ) -> None:
        """
        Preload configurations into cache.

        This method can be used to warm up the cache with frequently used
        configurations, improving performance for subsequent requests.

        Args:
            use_case_ids: List of use case IDs to preload (None for all active)
            intent_types: List of intent types to preload (None for all active)
        """
        logger.info("Starting configuration preload")

        # Preload by use_case_id
        if use_case_ids:
            for use_case_id in use_case_ids:
                try:
                    await self.load_config(use_case_id)
                except Exception as e:
                    logger.warning(
                        "Failed to preload config for use_case_id %s: %s",
                        use_case_id,
                        str(e),
                    )
        else:
            # Preload all active use cases
            try:
                stmt = select(UseCase).where(UseCase.is_active)
                result = await self.db_session.execute(stmt)
                use_cases = result.scalars().all()

                for use_case in use_cases:
                    try:
                        await self.load_config(use_case.use_case_id)
                    except Exception as e:
                        logger.warning(
                            "Failed to preload config for use_case_id %s: %s",
                            use_case.use_case_id,
                            str(e),
                        )
            except Exception as e:
                logger.error("Error preloading use case configs: %s", str(e))

        # Preload by intent_type
        if intent_types:
            for intent_type in intent_types:
                try:
                    if isinstance(intent_type, str):
                        intent_type = RequestType(intent_type)
                    await self.load_config_by_intent(intent_type)
                except Exception as e:
                    logger.warning(
                        "Failed to preload config for intent_type %s: %s",
                        intent_type,
                        str(e),
                    )
        else:
            # Preload all unique intent types
            try:
                intent_stmt = select(UseCase.intent_type).where(UseCase.is_active).distinct()
                result = await self.db_session.execute(intent_stmt)
                intent_type_rows = result.all()

                for (intent_type_str,) in intent_type_rows:
                    try:
                        intent_type = RequestType(intent_type_str)
                        await self.load_config_by_intent(intent_type)
                    except Exception as e:
                        logger.warning(
                            "Failed to preload config for intent_type %s: %s",
                            intent_type_str,
                            str(e),
                        )
            except Exception as e:
                logger.error("Error preloading intent type configs: %s", str(e))

        logger.info("Configuration preload completed. Cache stats: %s", self.get_cache_stats())


# Global cache for singleton pattern (optional)
_config_loader_cache: dict[str, UseCaseConfigLoader] = {}


def get_config_loader(
    db_session: AsyncSession, cache_key: str | None = None
) -> UseCaseConfigLoader:
    """
    Get a UseCaseConfigLoader instance with optional caching.

    This function provides a way to get UseCaseConfigLoader instances with
    optional singleton caching based on a cache key.

    Args:
        db_session: SQLAlchemy async database session
        cache_key: Optional cache key for singleton pattern (None for new instance)

    Returns:
        UseCaseConfigLoader instance
    """
    if cache_key and cache_key in _config_loader_cache:
        return _config_loader_cache[cache_key]

    loader = UseCaseConfigLoader(db_session)

    if cache_key:
        _config_loader_cache[cache_key] = loader

    return loader


def clear_global_cache() -> None:
    """
    Clear the global config loader cache.

    This function clears all cached UseCaseConfigLoader instances.
    It should be called when the application is shutting down or when
    a complete cache refresh is needed.
    """
    _config_loader_cache.clear()
    logger.debug("Cleared global config loader cache")
