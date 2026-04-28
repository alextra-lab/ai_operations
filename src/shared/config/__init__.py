"""
Centralized configuration management for the AI Operations Platform (AIOP) stack.

This module provides:
- Unified configuration schemas
- Environment variable loading with validation
- Service-specific configuration classes
- Configuration validation and defaults
"""

from .base import BaseConfig, ConfigManager, config_manager
from .schemas import (
    CircuitBreakerConfig,
    DatabaseConfig,
    EmbeddingConfig,
    InferenceGatewayConfig,
    JWTConfig,
    LLMGuardConfig,
    LoggingConfig,
    OpenTelemetryConfig,
    OrchestratorConfig,
    QdrantConfig,
    RateLimiterConfig,
    RedisConfig,
    RetrievalConfig,
    ServiceConfig,
    UsageLoggerConfig,
)
from .secrets import (
    EnvSecretProvider,
    SecretProvider,
    get_secret_provider,
    resolve_secret,
    set_secret_provider,
)
from .version import CONFIG_SCHEMA_VERSION, get_config_schema_version

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "BaseConfig",
    "CircuitBreakerConfig",
    "ConfigManager",
    "DatabaseConfig",
    "EmbeddingConfig",
    "EnvSecretProvider",
    "InferenceGatewayConfig",
    "JWTConfig",
    "LLMGuardConfig",
    "LoggingConfig",
    "OpenTelemetryConfig",
    "OrchestratorConfig",
    "QdrantConfig",
    "RateLimiterConfig",
    "RedisConfig",
    "RetrievalConfig",
    "SecretProvider",
    "ServiceConfig",
    "UsageLoggerConfig",
    "config_manager",
    "get_config_schema_version",
    "get_secret_provider",
    "resolve_secret",
    "set_secret_provider",
]
