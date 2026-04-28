"""
Provider Factory - instantiates correct provider based on type.

Routes provider configurations to appropriate provider classes:
- openai_compatible → OpenAIProvider (LLMaaS, vLLM, Ollama, etc.)
- mistral → MistralProvider
- azure_openai → AzureOpenAIProvider
- anthropic → AnthropicProvider
"""

from shared.logging_utils.fastapi import configure_logging  # type: ignore[import-untyped]

from ..providers.anthropic_provider import AnthropicProvider
from ..providers.azure_openai_provider import AzureOpenAIProvider
from ..providers.base import ProviderConfig
from ..providers.mistral_provider import MistralProvider
from ..providers.openai_provider import OpenAIProvider
from ..utils.errors import GatewayError

logger = configure_logging(service_name="provider_factory")


class ProviderFactory:
    """
    Factory for creating provider instances.

    Maps provider_type to provider class.
    """

    @staticmethod
    def create_provider(
        config: ProviderConfig,
    ) -> OpenAIProvider | MistralProvider | AzureOpenAIProvider | AnthropicProvider:
        """
        Create provider instance based on configuration.

        Args:
            config: Provider configuration from database

        Returns:
            Provider instance (OpenAI, Mistral, Azure, or Anthropic)

        Raises:
            GatewayError: Unknown provider type

        Example:
            ```python
            config = await provider_manager.get_provider("llmaas")
            provider = ProviderFactory.create_provider(config)

            response = await provider.chat_completion(request)
            ```
        """
        provider_type = config.provider_type.lower()

        logger.debug(
            "Creating provider instance",
            extra={
                "provider_name": config.name,
                "provider_type": provider_type,
            },
        )

        if provider_type in ("openai", "openai_compatible"):
            # Universal provider for:
            # - LLMaaS (LiteLLM)
            # - OpenAI Cloud
            # - vLLM
            # - Ollama
            # - LMStudio
            # - Groq
            # - Together.ai
            # - Any OpenAI-compatible API
            return OpenAIProvider(config)

        elif provider_type == "mistral":
            # Mistral Cloud API (mostly OpenAI-compatible)
            return MistralProvider(config)

        elif provider_type == "azure_openai":
            # Azure OpenAI Service (different URL structure)
            return AzureOpenAIProvider(config)

        elif provider_type == "anthropic":
            # Anthropic Claude (requires translation)
            # NOTE: Recommend using via LiteLLM instead
            return AnthropicProvider(config)

        else:
            raise GatewayError(
                f"Unknown provider type: {provider_type}. "
                f"Supported: openai_compatible, mistral, azure_openai, anthropic"
            )

    @staticmethod
    def get_supported_types() -> list[str]:
        """
        Get list of supported provider types.

        Returns:
            List of supported provider_type values
        """
        return [
            "openai_compatible",
            "mistral",
            "azure_openai",
            "anthropic",
        ]
