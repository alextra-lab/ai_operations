"""
Base configuration classes and utilities.
"""

import logging
import os
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseConfig")


class BaseConfig(BaseModel):
    """Base configuration class with common validation methods."""

    model_config = {
        "extra": "forbid",  # Strict validation - no extra fields
    }

    @classmethod
    def from_env(cls: type[T], **kwargs: Any) -> T:
        """Create configuration from environment variables."""
        env_data = {}
        for field_name, _field_info in cls.model_fields.items():
            env_var = field_name.upper()
            if env_var in os.environ:
                env_data[field_name] = os.environ[env_var]

        # Override with any explicit kwargs
        env_data.update(kwargs)
        return cls(**env_data)


class ConfigManager:
    """Centralized configuration manager for the AI Operations Platform (AIOP) stack."""

    def __init__(self) -> None:
        self._configs: dict[str, BaseConfig] = {}

    def register_config(self, name: str, config: BaseConfig) -> None:
        """Register a configuration instance."""
        self._configs[name] = config

    def get_config(self, name: str) -> BaseConfig | None:
        """Get a registered configuration by name."""
        return self._configs.get(name)

    def get_all_configs(self) -> dict[str, BaseConfig]:
        """Get all registered configurations."""
        return self._configs.copy()

    def validate_all(self) -> bool:
        """Validate all registered configurations."""
        try:
            for name, config in self._configs.items():
                if not isinstance(config, BaseConfig):
                    raise ValueError(f"Invalid config type for {name}: {type(config)}")
            return True
        except Exception as e:
            logger.error(
                "Configuration validation failed: %s",
                type(e).__name__,
                extra={"config_error_type": type(e).__name__},
            )
            return False


# Global configuration manager instance
config_manager = ConfigManager()
