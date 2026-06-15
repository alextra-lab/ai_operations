"""
Configuration models for embedding service providers and models.
"""

import os
from importlib.resources import files
from typing import Any, Literal

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

# Default configuration paths (resolved at import for tests)
_PACKAGE_CONFIG_DIR = os.path.realpath(os.path.dirname(__file__))
_BUILTIN_CONFIG_PATH = os.path.realpath(os.path.join(_PACKAGE_CONFIG_DIR, "models.yaml"))


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

        # Zero enabled providers is a valid state: the service starts deactivated and
        # returns 503 "No providers available" for embedding requests until an operator
        # enables one. (We intentionally do NOT require an enabled/default provider.)
        return v


def _load_yaml_mapping_from_literal(literal_path: Literal[
    "/opt/models/models.yaml",
    "/etc/embedding/models.yaml",
]) -> dict[str, Any] | None:
    """Load YAML from a fixed container path constant."""
    if not os.path.isfile(literal_path):
        return None

    with open(literal_path, encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file)

    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a mapping")
    return loaded


def _load_package_yaml_mapping() -> dict[str, Any] | None:
    """Load the package-bundled models.yaml without filesystem injection."""
    try:
        raw = files("app.config").joinpath("models.yaml").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a mapping")
    return loaded


def _load_user_yaml_mapping(config_path: str) -> dict[str, Any]:
    """Load YAML for a basename-only config path from the package config dir."""
    basename = os.path.basename(config_path)
    normalized = os.path.normpath(config_path)
    if basename != normalized or basename in {".", ".."} or not basename:
        raise ValueError("Configuration path must be a simple filename")

    raw = files("app.config").joinpath(basename).read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a mapping")
    return loaded


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
    if config_path:
        try:
            config_data = _load_user_yaml_mapping(config_path)
            logger.info("Configuration loaded successfully")
            return ServiceConfig(**config_data)
        except FileNotFoundError as exc:
            raise ValueError("Invalid configuration path") from exc
        except Exception as e:
            logger.error("Error loading configuration", extra={"error": str(e)})
            raise ValueError(f"Invalid configuration: {e!s}") from e

    for loader in (
        _load_package_yaml_mapping,
        lambda: _load_yaml_mapping_from_literal("/opt/models/models.yaml"),
        lambda: _load_yaml_mapping_from_literal("/etc/embedding/models.yaml"),
    ):
        try:
            config_data = loader()
        except Exception as e:
            logger.error("Error loading configuration", extra={"error": str(e)})
            raise ValueError(f"Invalid configuration: {e!s}") from e

        if config_data is not None:
            logger.info("Configuration loaded successfully")
            return ServiceConfig(**config_data)

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
