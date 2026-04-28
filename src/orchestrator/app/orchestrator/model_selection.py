"""
Model Selection for AI Operations Platform.

This module provides the ModelSelector class which handles:
- Loading intent model defaults from the database (ADR-069)
- Simple deterministic lookup: intent -> configured default model
- Caching defaults in memory for performance

Selection logic:
  1. Use case has config.models.llm set -> use that model (handled by LLMRouter)
  2. Otherwise -> look up intent default from intent_model_defaults table
  3. No default configured -> raise ValueError (surfaced in UI as "No default set")

No fallback chains. No heuristics. No hardcoded model names.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType

logger = configure_logging(service_name="model_selection", log_level="INFO", log_format="json")


async def load_intent_defaults_from_async_db(
    async_session: AsyncSession,
) -> tuple[dict[str, str], dict[str, float]]:
    """
    Load intent-to-model defaults and temperatures from async database session.

    Use this when you have AsyncSession (e.g. use_cases router) and need
    to populate ModelSelector. Pass the results to ModelSelector.

    Returns:
        Tuple of (model_defaults, temperature_defaults):
        - model_defaults: intent_code -> model_id
        - temperature_defaults: intent_code -> temperature (only for rows with temperature set)
    """
    result = await async_session.execute(
        text(
            "SELECT intent_code, model_id, temperature "
            "FROM intent_model_defaults "
            "WHERE is_active = TRUE "
            "ORDER BY priority ASC"
        )
    )
    model_defaults: dict[str, str] = {}
    temperature_defaults: dict[str, float] = {}
    for row in result:
        intent_code, model_id, temperature = row[0], row[1], row[2]
        model_defaults[intent_code] = model_id
        if temperature is not None:
            temperature_defaults[intent_code] = float(temperature)
    return model_defaults, temperature_defaults


class ModelSelector:
    """
    Deterministic intent-to-model lookup from database configuration (ADR-069).

    Admin sets default model per intent in the intent_model_defaults table
    via the Development UI. At runtime this class simply looks up the
    configured default. Nothing more.
    """

    def __init__(
        self,
        db: Session | None = None,
        preloaded_defaults: dict[str, str] | None = None,
        preloaded_temperatures: dict[str, float] | None = None,
    ) -> None:
        """
        Initialize the ModelSelector.

        Args:
            db: Optional sync database session for loading intent_model_defaults.
                When None and preloaded_defaults is None, cache is empty.
            preloaded_defaults: Optional pre-loaded intent->model mapping.
                Use when you have AsyncSession: call load_intent_defaults_from_async_db()
                and pass the first element of the result here.
            preloaded_temperatures: Optional intent->temperature overrides.
                Pass the second element from load_intent_defaults_from_async_db().
        """
        self.db = db
        self._intent_defaults_cache: dict[str, str] = {}
        self._intent_temperature_cache: dict[str, float] = {}

        if preloaded_defaults is not None:
            self._intent_defaults_cache = dict(preloaded_defaults)
            logger.info(
                "ModelSelector initialized with %d preloaded intent defaults",
                len(self._intent_defaults_cache),
            )
        elif self.db is not None:
            self._load_intent_defaults_from_db()
            logger.info(
                "ModelSelector initialized with %d intent defaults from db",
                len(self._intent_defaults_cache),
            )
        else:
            logger.warning(
                "ModelSelector initialized without db or preloaded_defaults; "
                "intent_model_defaults not loaded."
            )

        if preloaded_temperatures is not None:
            self._intent_temperature_cache = dict(preloaded_temperatures)

    def _load_intent_defaults_from_db(self) -> None:
        """Load active intent-to-model defaults from database into cache."""
        if self.db is None:
            return
        try:
            query = text(
                "SELECT intent_code, model_id, temperature "
                "FROM intent_model_defaults "
                "WHERE is_active = TRUE "
                "ORDER BY priority ASC"
            )
            result = self.db.execute(query)

            self._intent_defaults_cache = {}
            self._intent_temperature_cache = {}
            for row in result:
                intent_code, model_id = row[0], row[1]
                self._intent_defaults_cache[intent_code] = model_id
                if len(row) > 2 and row[2] is not None:
                    self._intent_temperature_cache[intent_code] = float(row[2])
                logger.info("Loaded intent default: %s -> %s", intent_code, model_id)

            # Log unconfigured intents
            all_intents = {rt.value for rt in RequestType}
            configured = set(self._intent_defaults_cache.keys())
            missing = all_intents - configured
            if missing:
                logger.warning(
                    "Intents without configured defaults: %s",
                    sorted(missing),
                )

        except Exception as e:
            logger.error("Failed to load intent model defaults: %s", str(e))
            self._intent_defaults_cache = {}

    def refresh_cache(self) -> None:
        """Reload defaults from database (e.g. after admin config change)."""
        logger.info("Refreshing intent model defaults cache")
        self._load_intent_defaults_from_db()

    def get_default_model(self, intent_type: RequestType) -> str | None:
        """
        Get the configured default model for an intent.

        Args:
            intent_type: The intent to look up.

        Returns:
            Model ID string, or None if no default is configured.
        """
        return self._intent_defaults_cache.get(intent_type.value)

    def get_model_for_intent(self, intent_type: RequestType) -> str:
        """
        Get the model for an intent, raising if not configured.

        Args:
            intent_type: The intent to look up.

        Returns:
            Model ID string.

        Raises:
            ValueError: If no default is configured for this intent.
        """
        model_id = self.get_default_model(intent_type)
        if not model_id:
            raise ValueError(
                f"No default model configured for intent {intent_type.value}. "
                f"Configure it in the Development UI."
            )
        return model_id

    def get_all_defaults(self) -> dict[str, str]:
        """Return a copy of all configured intent defaults."""
        return dict(self._intent_defaults_cache)

    def get_intent_temperature(self, intent_type: RequestType) -> float | None:
        """
        Get the configured temperature override for an intent, if any.

        Returns None if no override is configured (caller should use
        ParameterManager or ModelType default).
        """
        return self._intent_temperature_cache.get(intent_type.value)
