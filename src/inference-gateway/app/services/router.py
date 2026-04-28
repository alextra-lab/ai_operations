"""
Simple Router - model → provider lookup.

VERIFICATION CRITICAL:
- Queries existing models table (DON'T duplicate model registry)
- Uses shared.database.get_db (REUSE existing)
- Simple dictionary lookup (<1ms performance target)
- Follows ADR-052 (Model Routing and Provider Fallback)

P5-A15 VERIFIED (Nov 28, 2025):
- All methods are async (load_routes, route, reload, list_models)
- Uses `async with get_db() as session:` pattern
- Uses `await db.execute()` for all queries
"""

from shared.database import get_db  # type: ignore[import-untyped]
from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.errors import ModelNotFoundError

logger = configure_logging(service_name="simple_router")


class SimpleRouter:
    """
    Simple model → provider router.

    Implements ADR-052 v1: dictionary lookup (no fallback, no load balancing).
    Queries existing models table to build routes.
    """

    def __init__(self):
        self._routes: dict[str, str] = {}  # {model_id: provider_name}
        self._loaded = False

    async def load_routes(self, db: AsyncSession | None = None) -> None:
        """
        Load model → provider mappings from existing models table.

        VERIFICATION: Uses existing models table (src/backend/app/db/models.py).
        DON'T create new model registry.

        Args:
            db: Optional database session (creates new if not provided)
        """
        if db is None:
            async with get_db() as session:
                await self._load_from_db(session)
        else:
            await self._load_from_db(db)

        self._loaded = True
        logger.info("Loaded routes for %d model(s)", len(self._routes))

    async def _load_from_db(self, db: AsyncSession) -> None:
        """
        Internal: Load routes from models table joined with gateway_providers.

        Query structure:
        - Join models.provider with gateway_providers.name
        - Returns model_id → provider instance name mapping
        - Filter: model is_available = true, provider is_enabled = true
        - Local models (provider IS NULL) are not included (handled by Embedding Service)
        """
        # Simple join: model.provider → gateway_providers.name
        query = text(
            """
            SELECT
                m.model_id,
                gp.name as provider_name
            FROM models m
            INNER JOIN gateway_providers gp
                ON m.provider = gp.name
            WHERE m.is_available = true
              AND gp.is_enabled = true
            ORDER BY m.model_id
        """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        # Build routes dictionary
        self._routes.clear()
        for row in rows:
            model_id, provider_name = row
            self._routes[model_id] = provider_name

        logger.debug(
            "Loaded %d route(s)",
            len(self._routes),
            extra={"sample_routes": dict(list(self._routes.items())[:5])},
        )

    async def route(self, model_id: str) -> str:
        """
        Route model to Gateway provider.

        Performance target: <1ms (simple dict lookup).

        Args:
            model_id: Model identifier (e.g., "gpt-4o-mini")

        Returns:
            Gateway provider name (e.g., "LMStudio", "MyOpenAI")

        Raises:
            ModelNotFoundError: Model not found in registry
        """
        if not self._loaded:
            await self.load_routes()

        if model_id not in self._routes:
            raise ModelNotFoundError(model_id)

        return self._routes[model_id]

    async def reload(self) -> None:
        """
        Reload routes from database.

        Use this after model configuration changes.
        """
        logger.info("Reloading model routes")
        await self.load_routes()

    @property
    def is_loaded(self) -> bool:
        """Check if routes have been loaded."""
        return self._loaded

    def get_cached_route(self, model_id: str) -> str | None:
        """
        Get cached route without DB query (for performance).

        Returns None if not found (doesn't raise exception).
        """
        return self._routes.get(model_id)

    async def list_models(self) -> list[str]:
        """
        List all routable models.

        Returns:
            List of model IDs
        """
        if not self._loaded:
            await self.load_routes()

        return sorted(self._routes.keys())

    async def list_models_with_providers(self) -> list[dict[str, str]]:
        """
        List all routable models with their provider assignments.

        Returns:
            List of dicts with 'model_id' and 'provider' keys
        """
        if not self._loaded:
            await self.load_routes()

        return [
            {"model_id": model_id, "provider": provider_name}
            for model_id, provider_name in sorted(self._routes.items())
        ]

    async def get_route_map(self) -> dict[str, str]:
        """
        Get full route map for debugging/admin.

        Returns:
            Dictionary of {model_id: provider_name}
        """
        if not self._loaded:
            await self.load_routes()

        return dict(self._routes)
