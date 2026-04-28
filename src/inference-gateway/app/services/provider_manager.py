"""
Provider Manager - loads and caches provider configurations.

VERIFICATION:
- Uses shared.database.get_db (REUSE existing)
- Queries gateway_providers table (from P1-T2 migrations)
- In-memory cache to avoid repeated DB queries
- Follows existing service pattern (src/backend/app/services/)

P5-A15 VERIFIED (Nov 28, 2025):
- All methods are async (load_providers, get_provider, list_providers, reload)
- Uses `async with get_db() as session:` pattern
- Uses `await db.execute()` for all queries
"""

from shared.database import get_db  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..providers.base import ProviderConfig
from ..utils.errors import ProviderDisabledError, ProviderNotFoundError

logger = configure_logging(service_name="provider_manager")


class ProviderManager:
    """
    Manages provider configurations from database.

    Caches providers in memory to minimize DB queries.
    Follows ADR-051 (Provider Secrets and S2S Auth).
    """

    def __init__(self):
        self._cache: dict[str, ProviderConfig] = {}
        self._loaded = False

    async def load_providers(self, db: AsyncSession | None = None) -> None:
        """
        Load all enabled providers from database.

        Uses existing gateway_providers table (from P1-T2).

        Args:
            db: Optional database session (creates new if not provided)
        """
        if db is None:
            async with get_db() as session:
                await self._load_from_db(session)
        else:
            await self._load_from_db(db)

        self._loaded = True
        logger.info("Loaded %d provider(s)", len(self._cache))

    async def _load_from_db(self, db: AsyncSession) -> None:
        """Internal: Load providers from database."""
        # Query gateway_providers table
        query = text(
            """
            SELECT
                id::text as id,
                name,
                provider_type::text as provider_type,
                base_url,
                api_key_encrypted as api_key,
                is_enabled,
                priority,
                config_json,
                health_check_url,
                last_health_check,
                last_health_status
            FROM gateway_providers
            WHERE is_enabled = true
            ORDER BY priority ASC, name ASC
        """
        )

        result = await db.execute(query)
        rows = result.mappings().all()

        # Build cache
        self._cache.clear()
        for row in rows:
            config_json = row["config_json"] or {}
            last_health = row["last_health_check"] if "last_health_check" in row else None
            health_url = row["health_check_url"] if "health_check_url" in row else None
            health_status = row["last_health_status"] if "last_health_status" in row else None
            config = ProviderConfig(
                id=row["id"],
                name=row["name"],
                provider_type=row["provider_type"],
                base_url=row["base_url"],
                api_key=row["api_key"],
                is_enabled=row["is_enabled"],
                priority=row["priority"],
                config_json=config_json,
                timeout_seconds=config_json.get("timeout_seconds", 30.0),
                health_check_url=health_url,
                models=None,
                connection=None,
                last_health_check=str(last_health) if last_health is not None else None,
                last_health_status=health_status,
            )
            self._cache[config.name] = config

        logger.debug(
            "Loaded %d provider(s)",
            len(self._cache),
            extra={"providers": list(self._cache.keys())},
        )

    async def get_provider(self, name: str) -> ProviderConfig:
        """
        Get provider configuration by name.

        Args:
            name: Provider name (e.g., "openai", "mistral")

        Returns:
            ProviderConfig

        Raises:
            ProviderNotFoundError: Provider not found
            ProviderDisabledError: Provider is disabled
        """
        if not self._loaded:
            await self.load_providers()

        if name not in self._cache:
            raise ProviderNotFoundError(name)

        config = self._cache[name]
        if not config.is_enabled:
            raise ProviderDisabledError(name)

        return config

    async def list_providers(self, include_disabled: bool = False) -> list[ProviderConfig]:
        """
        List all providers.

        Args:
            include_disabled: Include disabled providers

        Returns:
            List of ProviderConfig
        """
        if not self._loaded:
            await self.load_providers()

        providers = list(self._cache.values())
        if not include_disabled:
            providers = [p for p in providers if p.is_enabled]

        return sorted(providers, key=lambda p: (p.priority, p.name))

    async def reload(self) -> None:
        """
        Reload providers from database.

        Use this after provider configuration changes.
        """
        logger.info("Reloading provider configurations")
        await self.load_providers()

    @property
    def is_loaded(self) -> bool:
        """Check if providers have been loaded."""
        return self._loaded

    def get_cached_provider(self, name: str) -> ProviderConfig | None:
        """
        Get cached provider without DB query (for performance).

        Returns None if not found (doesn't raise exception).
        """
        return self._cache.get(name)
