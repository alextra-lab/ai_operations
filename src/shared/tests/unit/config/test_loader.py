"""
Unit tests for the centralized configuration loader.

Tests the configuration loading functions and environment-aware database selection.
"""

import os
from unittest.mock import patch

from shared.config.loader import (
    _get_default_database_name,
    load_database_config,
    load_embedding_config,
    load_inference_gateway_config,
    load_jwt_config,
    load_llm_guard_config,
    load_logging_config,
    load_opentelemetry_config,
    load_orchestrator_config,
    load_qdrant_config,
    load_retrieval_config,
)
from shared.config.schemas import (
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
    UsageLoggerConfig,
)


class TestGetDefaultDatabaseName:
    """Tests for _get_default_database_name function."""

    def test_production_environment(self):
        """Test default database name for production (no flags)."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing flags
            os.environ.pop("TESTING", None)
            os.environ.pop("DEVELOPMENT", None)
            result = _get_default_database_name()
            assert result == "aio"

    def test_testing_environment(self):
        """Test default database name when TESTING=1."""
        with patch.dict(os.environ, {"TESTING": "1"}, clear=True):
            result = _get_default_database_name()
            assert result == "aio-test"

    def test_development_environment(self):
        """Test default database name when DEVELOPMENT=1."""
        with patch.dict(os.environ, {"DEVELOPMENT": "1"}, clear=True):
            result = _get_default_database_name()
            assert result == "aio"

    def test_testing_takes_precedence_over_development(self):
        """Test that TESTING flag takes precedence over DEVELOPMENT."""
        with patch.dict(os.environ, {"TESTING": "1", "DEVELOPMENT": "1"}, clear=True):
            result = _get_default_database_name()
            assert result == "aio-test"

    def test_non_truthy_testing_value(self):
        """Test that TESTING=0 is not treated as testing environment."""
        with patch.dict(os.environ, {"TESTING": "0"}, clear=True):
            result = _get_default_database_name()
            assert result == "aio"

    def test_non_truthy_development_value(self):
        """Test that DEVELOPMENT=0 is not treated as development environment."""
        with patch.dict(os.environ, {"DEVELOPMENT": "0"}, clear=True):
            result = _get_default_database_name()
            assert result == "aio"


class TestLoadDatabaseConfig:
    """Tests for load_database_config function."""

    def test_explicit_postgres_db_overrides_default(self):
        """Test that explicit POSTGRES_DB overrides environment-aware default."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DB": "custom_database",
                "TESTING": "1",
                "POSTGRES_USER": "testuser",
                "POSTGRES_PASSWORD": "testpass",
            },
            clear=True,
        ):
            config = load_database_config()
            assert config.database == "custom_database"

    def test_uses_environment_default_when_no_explicit_db(self):
        """Test that environment-aware default is used when POSTGRES_DB not set."""
        with patch.dict(
            os.environ,
            {
                "TESTING": "1",
                "POSTGRES_USER": "testuser",
                "POSTGRES_PASSWORD": "testpass",
            },
            clear=True,
        ):
            # Ensure POSTGRES_DB is not set
            os.environ.pop("POSTGRES_DB", None)
            config = load_database_config()
            assert config.database == "aio-test"

    def test_returns_database_config_type(self):
        """Test that load_database_config returns DatabaseConfig instance."""
        config = load_database_config()
        assert isinstance(config, DatabaseConfig)

    def test_loads_all_database_fields(self):
        """Test that all database config fields are loaded."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "myuser",
                "POSTGRES_PASSWORD": "mypassword",
                "POSTGRES_HOST": "myhost",
                "POSTGRES_PORT": "5433",
                "POSTGRES_DB": "mydb",
                "POSTGRES_MAX_CONNECTIONS": "50",
                "POSTGRES_CONNECTION_TIMEOUT": "60",
                "DB_POOL_SIZE": "25",
                "DB_MAX_OVERFLOW": "30",
                "DB_POOL_RECYCLE": "1800",
                "DB_POOL_PRE_PING": "false",
            },
            clear=True,
        ):
            config = load_database_config()
            assert config.user == "myuser"
            assert config.password == "mypassword"
            assert config.host == "myhost"
            assert config.port == 5433
            assert config.database == "mydb"
            assert config.max_connections == 50
            assert config.connection_timeout == 60
            assert config.pool_size == 25
            assert config.max_overflow == 30
            assert config.pool_recycle == 1800
            assert config.pool_pre_ping is False

    def test_get_connection_string(self):
        """Test that get_connection_string works correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "testdb",
            },
            clear=True,
        ):
            config = load_database_config()
            conn_str = config.get_connection_string(async_driver=True)
            assert "asyncpg" in conn_str
            assert "user:pass@localhost:5432/testdb" in conn_str


class TestLoadQdrantConfig:
    """Tests for load_qdrant_config function."""

    def test_returns_qdrant_config_type(self):
        """Test that load_qdrant_config returns QdrantConfig instance."""
        config = load_qdrant_config()
        assert isinstance(config, QdrantConfig)

    def test_loads_qdrant_defaults(self):
        """Test that default Qdrant values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_qdrant_config()
            assert config.host == "vector-db"
            assert config.port == 6333
            assert config.collection_name == "documents"
            assert config.vector_size == 384
            assert config.indexing_threshold == 20000


class TestLoadJWTConfig:
    """Tests for load_jwt_config function."""

    def test_returns_jwt_config_type(self):
        """Test that load_jwt_config returns JWTConfig instance."""
        config = load_jwt_config()
        assert isinstance(config, JWTConfig)

    def test_loads_jwt_defaults(self):
        """Test that default JWT values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_jwt_config()
            assert config.algorithm == "HS256"
            assert config.issuer == "ai-operations-platform"
            assert config.access_token_expire_minutes == 30


class TestLoadLoggingConfig:
    """Tests for load_logging_config function."""

    def test_returns_logging_config_type(self):
        """Test that load_logging_config returns LoggingConfig instance."""
        config = load_logging_config()
        assert isinstance(config, LoggingConfig)

    def test_accepts_service_name_parameter(self):
        """Test that service_name parameter is used."""
        config = load_logging_config(service_name="my-service")
        assert config.service_name == "my-service"

    def test_respects_redaction_environment_variables(self):
        """Test that redaction flags are loaded from environment variables."""
        with patch.dict(
            os.environ,
            {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "full"},
            clear=True,
        ):
            config = load_logging_config()
            assert config.redact_logs is True
            assert config.redaction_level == "full"

    def test_loads_verbose_flag(self):
        """Test that LOG_VERBOSE is loaded from environment variables."""
        with patch.dict(os.environ, {"LOG_VERBOSE": "true"}, clear=True):
            config = load_logging_config()
            assert config.verbose is True


class TestLoadOpenTelemetryConfig:
    """Tests for load_opentelemetry_config function."""

    def test_returns_opentelemetry_config_type(self):
        """Test that load_opentelemetry_config returns OpenTelemetryConfig."""
        config = load_opentelemetry_config()
        assert isinstance(config, OpenTelemetryConfig)

    def test_disabled_by_default(self):
        """Test that OpenTelemetry is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_opentelemetry_config()
            assert config.enabled is False


class TestLoadEmbeddingConfig:
    """Tests for load_embedding_config function."""

    def test_returns_embedding_config_type(self):
        """Test that load_embedding_config returns EmbeddingConfig instance."""
        config = load_embedding_config()
        assert isinstance(config, EmbeddingConfig)

    def test_loads_embedding_defaults(self):
        """Test that default embedding values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_embedding_config()
            assert config.name == "embedding-service"
            assert config.model_name == "all-minilm-l6-v2"
            assert config.batch_size == 32

    def test_loads_embedding_prefixed_fields(self):
        """Test embedding loader reads EMBEDDING_* variables from compose/template names."""
        with patch.dict(
            os.environ,
            {
                "EMBEDDING_HOST": "embedding-host",
                "EMBEDDING_PORT": "8100",
                "EMBEDDING_DEBUG": "true",
                "EMBEDDING_ENABLE_CORS": "false",
                "EMBEDDING_CORS_ORIGINS": "https://example.com",
                "EMBEDDING_MODEL_CACHE_DIR": "/tmp/models",
                "EMBEDDING_ENABLE_MODEL_CACHING": "false",
                "EMBEDDING_SERVICE_CLIENT_API_KEY": "client-key",
            },
            clear=True,
        ):
            config = load_embedding_config()
            assert config.host == "embedding-host"
            assert config.port == 8100
            assert config.debug is True
            assert config.enable_cors is False
            assert config.cors_origins == ["https://example.com"]
            assert config.model_cache_dir == "/tmp/models"
            assert config.enable_model_caching is False
            assert config.client_api_key == "client-key"


class TestLoadRetrievalConfig:
    """Tests for load_retrieval_config function."""

    def test_returns_retrieval_config_type(self):
        """Test that load_retrieval_config returns RetrievalConfig instance."""
        config = load_retrieval_config()
        assert isinstance(config, RetrievalConfig)

    def test_loads_retrieval_defaults(self):
        """Test that default retrieval values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_retrieval_config()
            assert config.name == "corpus-service"
            assert config.port == 8001
            assert config.chunk_size == 1000

    def test_loads_retrieval_prefixed_fields(self):
        """Test retrieval loader reads CORPUS_* variables from compose/template names."""
        with patch.dict(
            os.environ,
            {
                "CORPUS_HOST": "corpus-host",
                "CORPUS_PORT": "8101",
                "CORPUS_DEBUG": "true",
                "CORPUS_ENABLE_CORS": "false",
                "CORPUS_CORS_ORIGINS": "https://example.com",
                "CORPUS_DOCUMENTS_PATH": "/tmp/docs",
                "CORPUS_TEMP_PATH": "/tmp/data",
                "CORPUS_CHUNK_SIZE": "222",
                "CORPUS_CHUNK_OVERLAP": "22",
                "CORPUS_MAX_CHUNKS_PER_DOCUMENT": "333",
                "CORPUS_EMBEDDING_SERVICE_TOKEN": "token",
            },
            clear=True,
        ):
            config = load_retrieval_config()
            assert config.host == "corpus-host"
            assert config.port == 8101
            assert config.debug is True
            assert config.enable_cors is False
            assert config.cors_origins == ["https://example.com"]
            assert config.documents_path == "/tmp/docs"
            assert config.temp_path == "/tmp/data"
            assert config.chunk_size == 222
            assert config.chunk_overlap == 22
            assert config.max_chunks_per_document == 333
            assert config.embedding_service_token == "token"


class TestLoadOrchestratorConfig:
    """Tests for load_orchestrator_config function."""

    def test_returns_orchestrator_config_type(self):
        """Test that load_orchestrator_config returns OrchestratorConfig."""
        config = load_orchestrator_config()
        assert isinstance(config, OrchestratorConfig)

    def test_loads_orchestrator_defaults(self):
        """Test that default orchestrator values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_orchestrator_config()
            assert config.name == "orchestrator-api"
            assert config.port == 8000
            assert config.llm_guard_enabled is True
            assert config.retrieval_enabled is True
            assert config.transcript_storage_enabled is False
            assert config.dashboard_health_endpoints == {}


class TestLoadInferenceGatewayConfig:
    """Tests for load_inference_gateway_config function."""

    def test_returns_inference_gateway_config_type(self):
        """Test that load_inference_gateway_config returns InferenceGatewayConfig."""
        config = load_inference_gateway_config()
        assert isinstance(config, InferenceGatewayConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert isinstance(config.rate_limiter, RateLimiterConfig)
        assert isinstance(config.usage_logger, UsageLoggerConfig)

    def test_loads_inference_gateway_defaults(self):
        """Test that default inference gateway values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_inference_gateway_config()
            assert config.name == "inference-gateway"
            assert config.port == 8002
            assert config.redis.enabled is True
            assert config.circuit_breaker.failure_threshold == 3
            assert config.rate_limiter.enabled is True
            assert config.usage_logger.batch_size == 10


class TestLoadLLMGuardConfig:
    """Tests for load_llm_guard_config function."""

    def test_returns_llm_guard_config_type(self):
        """Test that load_llm_guard_config returns LLMGuardConfig instance."""
        config = load_llm_guard_config()
        assert isinstance(config, LLMGuardConfig)

    def test_loads_llm_guard_defaults(self):
        """Test that default LLM Guard values are loaded."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_llm_guard_config()
            assert config.name == "llm-guard-svc"
            assert config.enabled is True
            assert config.cache_enabled is True
            assert config.cache_max_size == 1000


class TestConfigManagerFunctions:
    """Tests for config manager utility functions."""

    def test_load_all_configs(self):
        """Test that load_all_configs loads all configuration types."""
        from shared.config.loader import load_all_configs

        configs = load_all_configs()
        assert "database" in configs
        assert "qdrant" in configs
        assert "jwt" in configs
        assert "logging" in configs
        assert "opentelemetry" in configs
        assert "embedding" in configs
        assert "retrieval" in configs
        assert "orchestrator" in configs
        assert "llm_guard" in configs
        assert "inference_gateway" in configs

    def test_get_config(self):
        """Test that get_config retrieves registered configs."""
        from shared.config.loader import get_config, load_database_config

        # Load a config first
        load_database_config()

        # Then retrieve it
        config = get_config("database")
        assert config is not None
        assert isinstance(config, DatabaseConfig)

    def test_get_config_nonexistent(self):
        """Test that get_config returns None for non-existent config."""
        from shared.config.loader import get_config

        config = get_config("nonexistent_config")
        assert config is None

    def test_validate_all_configs(self):
        """Test that validate_all_configs returns True for valid configs."""
        from shared.config.loader import load_all_configs, validate_all_configs

        load_all_configs()
        result = validate_all_configs()
        assert result is True
