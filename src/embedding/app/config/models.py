"""
Configuration models for embedding service providers and models.
"""

import os
from typing import Any

import yaml
from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from shared.config.loader import load_embedding_config
from shared.logging_utils.fastapi import configure_logging
from shared.providers import (
    ConnectionConfig,
    ModelConfig,
)
from shared.providers import (
    ProviderConfig as BaseProviderConfig,
)

# Use relative import instead of absolute to avoid circular dependency

# Configure structured logger for this module
logger = configure_logging(service_name="embedding_config")

# Default configuration paths
DEFAULT_CONFIG_PATHS = [
    "/opt/models/models.yaml",  # Bind-mounted volume
    "/etc/embedding/models.yaml",  # Container config path
    os.path.join(os.path.dirname(__file__), "models.yaml"),  # Package default
]


# Re-export shared models for backward compatibility
# Embedding service uses these extensively in YAML config
# Note: Don't reassign ModelConfig to itself, just use the imported one
OpenAIConnectionConfig = ConnectionConfig  # Alias for backward compatibility


class ProviderConfig(BaseProviderConfig):
    """
    Embedding service provider configuration.

    Extends shared ProviderConfig with embedding-specific validation.
    YAML fields 'type' and 'enabled' are mapped to 'provider_type' and 'is_enabled'.
    """

    # Override to make these required for embedding service
    models: list[ModelConfig] = Field(..., description="Models available through this provider")

    @model_validator(mode="before")
    @classmethod
    def map_yaml_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Map YAML field names to shared model field names."""
        # Map 'type' -> 'provider_type'
        if "type" in values and "provider_type" not in values:
            provider_type_val = values["type"]
            # Convert ProviderType enum to string if needed
            if hasattr(provider_type_val, "value"):
                values["provider_type"] = provider_type_val.value
            else:
                values["provider_type"] = str(provider_type_val)

        # Map 'enabled' -> 'is_enabled'
        if "enabled" in values and "is_enabled" not in values:
            values["is_enabled"] = values["enabled"]

        # Ensure base_url is set (required by base model)
        if "base_url" not in values:
            # For local models, use placeholder
            if values.get("provider_type") in ["local", "local_model"]:
                values["base_url"] = "http://localhost:8000"
            # For OpenAI-compatible, try to get from connection
            elif "connection" in values and isinstance(values["connection"], dict):
                values["base_url"] = values["connection"].get("url", "http://localhost:8000")
            else:
                values["base_url"] = "http://localhost:8000"

        return values

    @model_validator(mode="after")
    def check_provider_config(self) -> "ProviderConfig":
        """Validate provider configuration after all fields are processed."""

        if not self.models:
            raise ValueError("At least one model must be specified for a provider.")

        # Convert provider_type to ProviderType enum if it's a string
        provider_type_str = str(self.provider_type).lower()

        if (
            provider_type_str in ["openai_compatible", "openai"]
            and self.is_enabled
            and self.connection is None
        ):
            raise ValueError(
                f"Provider '{self.name}': OpenAI-compatible providers that are enabled must have connection details."
            )

        if provider_type_str in ["local_model", "local"]:
            for model_config in self.models:
                if not model_config.path:
                    raise ValueError(
                        f"Provider '{self.name}', Model '{model_config.name}': Local models must have a path."
                    )

        # Ensure at least one model is default if the provider is enabled
        if self.is_enabled:
            default_models = [m for m in self.models if m.default]
            if not default_models and self.models:  # if models list is not empty
                self.models[0].default = True
                logger.info(
                    f"Provider '{self.name}': Set first model '{self.models[0].name}' as default."
                )
            elif not self.models:
                logger.warning(f"Provider '{self.name}' has no models defined.")

        return self


class ServiceConfig(BaseModel):
    """Top-level configuration for embedding service."""

    default_provider: str | None = Field(None, description="Default provider name")
    providers: list[ProviderConfig] = Field(..., description="Available providers")

    @field_validator("providers")
    @classmethod
    def validate_providers(
        cls,
        v: list["ProviderConfig"],
        _info: ValidationInfo,
    ) -> list["ProviderConfig"]:
        """Validate providers configuration."""
        if not v:
            raise ValueError("At least one provider must be specified")

        # Validate provider names are unique
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Provider names must be unique")

        # Ensure default provider is set and enabled
        default_provider = None
        for provider in v:
            if provider.is_enabled and (
                default_provider is None or provider.priority < default_provider.priority
            ):
                default_provider = provider

        if default_provider is None:
            raise ValueError("At least one provider must be enabled")

        return v


def load_config(config_path: str | None = None) -> ServiceConfig:
    """
    Load service configuration from YAML file.

    Args:
        config_path: Path to configuration file (optional)

    Returns:
        ServiceConfig: Parsed and validated configuration

    Raises:
        FileNotFoundError: If no configuration file is found
        ValueError: If configuration is invalid
    """
    paths_to_try = [config_path] if config_path else []
    paths_to_try.extend(DEFAULT_CONFIG_PATHS)

    for path in paths_to_try:
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    config_data = yaml.safe_load(f)
                    logger.info("Configuration loaded successfully")
                    return ServiceConfig(**config_data)
            except Exception as e:
                logger.error(f"Error loading configuration from {path}: {e!s}")
                raise ValueError(f"Invalid configuration: {e!s}")

    # If no explicit path is provided and no default files exist, use environment-based config
    if not config_path:
        try:
            return create_default_config_from_env()
        except Exception as e:
            logger.error(f"Error creating configuration from environment: {e!s}")
            raise ValueError(f"Failed to create configuration: {e!s}")

    raise FileNotFoundError("No configuration file found")


def create_default_config_from_env() -> ServiceConfig:
    """
    Create a default configuration based on environment variables.

    Returns:
        ServiceConfig: Default configuration
    """
    providers = []

    embedding_config = load_embedding_config()
    # Try to set up OpenAI-compatible provider if URL is provided
    openai_url = embedding_config.openai_base_url
    openai_api_key = embedding_config.openai_api_key
    if openai_url and openai_api_key:
        providers.append(
            ProviderConfig(
                id=None,
                name="openai",
                provider_type="openai_compatible",
                base_url=openai_url,
                api_key=None,
                health_check_url=None,
                last_health_check=None,
                last_health_status=None,
                is_enabled=True,
                priority=10,
                connection=OpenAIConnectionConfig(
                    url=openai_url,
                    auth_type="API_KEY",
                    api_key_env="OPENAI_API_KEY",
                    timeout_seconds=30,
                    max_retries=3,
                ),
                models=[
                    ModelConfig(
                        name="text-embedding-3-small",
                        dimensions=384,
                        default=True,
                        server_model_name="text-embedding-3-small",
                        path=None,
                        batch_size=32,
                        metadata=None,
                    )
                ],
            )
        )

    # Set up local model provider if model path exists
    model_dir = embedding_config.model_cache_dir
    model_path = os.path.join(model_dir, "all-minilm-l6-v2")
    if os.path.exists(model_path):
        providers.append(
            ProviderConfig(
                id=None,
                name="local",
                provider_type="local",
                base_url="http://localhost:8000",  # Placeholder for local models
                api_key=None,
                health_check_url=None,
                last_health_check=None,
                last_health_status=None,
                is_enabled=True,
                priority=(20 if providers else 10),  # Higher priority if no OpenAI provider
                connection=None,
                models=[
                    ModelConfig(
                        name="all-minilm-l6-v2",
                        dimensions=384,
                        path=model_path,
                        default=len(providers) == 0,  # Default if no OpenAI provider
                        batch_size=32,
                        server_model_name=None,
                        metadata=None,
                    )
                ],
            )
        )

    if not providers:
        # Create a dummy local provider as placeholder
        providers.append(
            ProviderConfig(
                id=None,
                name="local",
                provider_type="local",
                base_url="http://localhost:8000",  # Placeholder for local models
                api_key=None,
                health_check_url=None,
                last_health_check=None,
                last_health_status=None,
                is_enabled=True,
                priority=10,
                connection=None,
                models=[
                    ModelConfig(
                        name="all-minilm-l6-v2",
                        dimensions=384,
                        path="/opt/models/all-minilm-l6-v2",  # This will fail at runtime if not present
                        default=True,
                        batch_size=32,
                        server_model_name=None,
                        metadata=None,
                    )
                ],
            )
        )
        logger.warning(
            "Created default configuration with dummy local provider. Models may not be available."
        )

    return ServiceConfig(default_provider=None, providers=providers)
