"""
Factory for creating and managing embedding providers.
"""

from typing import Any

from shared.config.schemas import EmbeddingConfig
from shared.logging_utils.fastapi import configure_logging

from ..config.models import ServiceConfig, load_config

# Use relative imports
from ..types import ProviderType
from .local import LocalProvider
from .openai import OpenAIProvider
from .protocol import EmbeddingProvider, ProviderNotAvailableError

# Configure structured logger for this module
logger = configure_logging(service_name="provider_factory")


class ProviderFactory:
    """Factory for creating and managing embedding providers."""

    def __init__(self) -> None:
        """Initialize the provider factory."""
        self.providers: dict[str, EmbeddingProvider] = {}
        self.provider_registry: dict[ProviderType, type] = {
            ProviderType.OPENAI_COMPATIBLE: OpenAIProvider,
            ProviderType.LOCAL_MODEL: LocalProvider,
        }
        self.config: ServiceConfig | None = None
        self.default_provider: str | None = None

    async def load_providers(
        self,
        config_path: str | None = None,
        embedding_settings: EmbeddingConfig | None = None,
    ) -> dict[str, bool]:
        """
        Load providers from configuration.

        Args:
            config_path: Optional path to configuration file

        Returns:
            dict: Mapping of provider names to initialization success
        """
        # Clear existing providers
        self.providers = {}

        # Load configuration
        try:
            self.config = load_config(config_path)
        except Exception as e:
            logger.error(f"Error loading configuration: {e!s}")
            raise ValueError(f"Failed to load configuration: {e!s}")

        # Initialize providers
        results = {}

        for provider_config in self.config.providers:
            if not provider_config.is_enabled:
                logger.info(f"Provider {provider_config.name} is disabled, skipping")
                results[provider_config.name] = False
                continue

            try:
                # Normalize to ProviderType for type-safe registry lookup (config may be str)
                pt_raw = provider_config.provider_type
                provider_type: ProviderType = (
                    pt_raw
                    if isinstance(pt_raw, ProviderType)
                    else ProviderType(str(pt_raw).upper())
                )
                if provider_type not in self.provider_registry:
                    logger.warning(
                        f"No implementation for provider type {provider_config.provider_type}"
                    )
                    results[provider_config.name] = False
                    continue

                provider_class = self.provider_registry[provider_type]

                current_provider: EmbeddingProvider | None = None
                if provider_type == ProviderType.OPENAI_COMPATIBLE:
                    if not provider_config.connection:
                        logger.error(
                            f"Missing connection configuration for OpenAI provider {provider_config.name}"
                        )
                        results[provider_config.name] = False
                        continue

                    api_key_override = (
                        embedding_settings.openai_api_key
                        if embedding_settings and embedding_settings.openai_api_key
                        else provider_config.api_key
                    )
                    current_provider = provider_class(
                        name=provider_config.name,
                        connection_config=provider_config.connection,
                        models=provider_config.models,
                        priority=provider_config.priority,
                        api_key=api_key_override,
                    )
                elif provider_type == ProviderType.LOCAL_MODEL:
                    current_provider = provider_class(
                        name=provider_config.name,
                        models=provider_config.models,
                        priority=provider_config.priority,
                    )

                if current_provider:
                    self.providers[provider_config.name] = current_provider
                    results[provider_config.name] = True
                    logger.info(f"Successfully loaded provider {provider_config.name}")

            except Exception as e:
                logger.error(f"Error initializing provider {provider_config.name}: {e!s}")
                results[provider_config.name] = False

        # Set default provider
        await self._set_default_provider()

        return results

    async def _set_default_provider(self) -> None:
        """
        Set the default provider based on priority.

        The provider with the lowest priority value becomes the default.
        """
        if not self.providers:
            self.default_provider = None
            return

        # Use configured default provider if available
        if self.config and self.config.default_provider:
            if self.config.default_provider in self.providers:
                self.default_provider = self.config.default_provider
                logger.info(f"Using configured default provider: {self.default_provider}")
                return
            logger.warning(
                f"Configured default provider {self.config.default_provider} not available"
            )

        # Otherwise, use provider with lowest priority value
        ordered_providers = sorted(
            self.providers.items(),
            key=lambda x: getattr(x[1], "priority", 100),
        )

        if ordered_providers:
            self.default_provider = ordered_providers[0][0]
            logger.info(f"Selected default provider by priority: {self.default_provider}")
        else:
            self.default_provider = None
            logger.warning("No providers available")

    async def get_provider(self, name: str | None = None) -> "EmbeddingProvider":
        """
        Get a provider by name, or the default provider if name is None.

        Args:
            name: Provider name (optional, defaults to default provider)

        Returns:
            EmbeddingProvider: The requested provider

        Raises:
            ProviderNotAvailableError: If the requested provider is not available
        """
        if not self.providers:
            raise ProviderNotAvailableError("No providers available")

        # If name is provided, return that provider
        if name:
            if name in self.providers:
                return self.providers[name]
            raise ProviderNotAvailableError(f"Provider {name} not found")

        # Otherwise, return default provider
        if not self.default_provider or self.default_provider not in self.providers:
            # Fallback to first available provider
            provider_name = next(iter(self.providers.keys()))
            logger.warning(f"Default provider not set, using first available: {provider_name}")
            return self.providers[provider_name]

        return self.providers[self.default_provider]

    async def get_provider_health(self) -> dict[str, dict[str, Any]]:
        """
        Get health status for all providers.

        Returns:
            dict: Mapping of provider names to health status
        """
        health: dict[str, dict[str, Any]] = {}
        for name, provider in self.providers.items():
            try:
                provider_health = await provider.health_check()
                health[name] = provider_health
            except Exception as e:
                logger.error(f"Error checking health for provider {name}: {e!s}")
                health[name] = {"available": False, "error": str(e)}

        return health

    async def get_available_models(self) -> dict[str, dict[str, Any]]:
        """
        Get information about available models across all providers.

        Returns:
            dict: Mapping of provider names to model information
        """
        models: dict[str, dict[str, Any]] = {}
        for name, provider in self.providers.items():
            try:
                provider_models = await provider.get_model_info()
                models[name] = provider_models
            except Exception as e:
                logger.error(f"Error getting models for provider {name}: {e!s}")
                models[name] = {"error": str(e)}

        return models

    async def find_provider_for_model(self, model_name: str) -> "EmbeddingProvider | None":
        """
        Find which provider has the specified model.

        Args:
            model_name: The model name to search for

        Returns:
            EmbeddingProvider if found, None otherwise
        """
        for provider_name, provider in self.providers.items():
            try:
                model_info = await provider.get_model_info()
                if model_name in model_info:
                    logger.info(f"Found model {model_name} in provider {provider_name}")
                    return provider
            except Exception as e:
                logger.debug(f"Error checking provider {provider_name} for model {model_name}: {e}")
                continue
        return None

    def register_provider_type(self, provider_type: ProviderType, provider_class: type) -> None:
        """
        Register a new provider type.

        Args:
            provider_type: The provider type
            provider_class: The provider class
        """
        self.provider_registry[provider_type] = provider_class
        logger.info(f"Registered provider type {provider_type}")


# Global factory instance
factory = ProviderFactory()
