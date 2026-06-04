"""
Configuration loader for the AI Operations Platform (AIOP) stack.
"""

from __future__ import annotations

import json
import os

from .base import BaseConfig, config_manager
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
    UsageLoggerConfig,
)
from .secrets import resolve_secret


def _get_default_database_name() -> str:
    """
    Get the default database name based on environment.

    Environment-aware database selection:
    - TESTING=1: aio-test
    - Production: aio
    """
    testing = os.environ.get("TESTING", "0") == "1"

    if testing:
        return "aio-test"
    return "aio"


def is_testing_environment() -> bool:
    """Return True when running in test mode."""
    return os.environ.get("TESTING", "0") == "1"


def load_database_config() -> DatabaseConfig:
    """Load database configuration from environment variables."""
    # Use explicit POSTGRES_DB if set, otherwise use environment-aware default
    db_name = os.environ.get("POSTGRES_DB") or _get_default_database_name()

    password: str = (
        resolve_secret("POSTGRES_PASSWORD")
        or os.environ.get("POSTGRES_PASSWORD", "test_password_123")
        or "test_password_123"
    )
    config = DatabaseConfig(
        user=os.environ.get("POSTGRES_USER", "testuser"),
        password=password,
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=db_name,
        ssl_mode=os.environ.get("POSTGRES_SSL_MODE"),
        max_connections=int(os.environ.get("POSTGRES_MAX_CONNECTIONS", "20")),
        connection_timeout=int(os.environ.get("POSTGRES_CONNECTION_TIMEOUT", "30")),
        pool_size=int(os.environ.get("DB_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "20")),
        pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "3600")),
        pool_pre_ping=os.environ.get("DB_POOL_PRE_PING", "true").lower()
        in ("true", "1", "yes", "on"),
    )

    config_manager.register_config("database", config)
    return config


def load_qdrant_config() -> QdrantConfig:
    """Load Qdrant configuration from environment variables."""
    config = QdrantConfig(
        host=os.environ.get("QDRANT_HOST", "vector-db"),
        port=int(os.environ.get("QDRANT_PORT", "6333")),
        url=os.environ.get("QDRANT_URL"),
        api_key=resolve_secret("QDRANT_API_KEY"),
        prefer_grpc=os.environ.get("QDRANT_PREFER_GRPC", "false").lower() == "true",
        timeout=float(os.environ.get("QDRANT_TIMEOUT", "10.0")),
        collection_name=os.environ.get("QDRANT_COLLECTION", "documents"),
        vector_size=int(os.environ.get("QDRANT_VECTOR_SIZE", "384")),
        distance=os.environ.get("QDRANT_DISTANCE", "COSINE"),
        m=int(os.environ.get("QDRANT_HNSW_M", "16")),
        ef_construct=int(os.environ.get("QDRANT_HNSW_EF_CONSTRUCT", "100")),
        ef_search=int(os.environ.get("QDRANT_HNSW_EF_SEARCH", "128")),
        default_limit=int(os.environ.get("QDRANT_DEFAULT_LIMIT", "10")),
        default_offset=int(os.environ.get("QDRANT_DEFAULT_OFFSET", "0")),
        indexing_threshold=int(os.environ.get("QDRANT_INDEXING_THRESHOLD", "20000")),
    )

    config_manager.register_config("qdrant", config)
    return config


def load_jwt_config() -> JWTConfig:
    """Load JWT configuration from environment variables."""
    raw = resolve_secret("JWT_SECRET") or os.environ.get("JWT_SECRET", "CHANGE_ME") or "CHANGE_ME"
    secret: str = raw if raw is not None else "CHANGE_ME"
    config = JWTConfig(
        secret=secret,
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
        issuer=os.environ.get("JWT_ISSUER", "ai-operations-platform"),
        access_token_expire_minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        refresh_token_expire_days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    )

    config_manager.register_config("jwt", config)
    return config


def load_logging_config(service_name: str = "unknown") -> LoggingConfig:
    """Load logging configuration from environment variables."""
    config = LoggingConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format=os.environ.get("LOG_FORMAT", "json"),
        service_name=service_name,
        enable_structured_logging=os.environ.get("LOG_ENABLE_STRUCTURED", "true").lower() == "true",
        enable_request_id=os.environ.get("LOG_ENABLE_REQUEST_ID", "true").lower() == "true",
        verbose=os.environ.get("LOG_VERBOSE", "false").lower() == "true",
        redact_logs=os.environ.get("REDACT_LOGS", "false").lower() in ("true", "1", "yes"),
        redaction_level=os.environ.get("LOG_REDACTION_LEVEL", "partial"),
    )

    config_manager.register_config("logging", config)
    return config


def load_opentelemetry_config() -> OpenTelemetryConfig:
    """Load OpenTelemetry configuration from environment variables."""
    config = OpenTelemetryConfig(
        enabled=os.environ.get("OTEL_ENABLED", "false").lower() == "true",
        endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
        service_name=os.environ.get("OTEL_SERVICE_NAME", "aio"),
        service_version=os.environ.get("OTEL_SERVICE_VERSION", "1.0.0"),
        environment=os.environ.get("ENV", "development"),
    )

    config_manager.register_config("opentelemetry", config)
    return config


def load_embedding_config() -> EmbeddingConfig:
    """Load embedding service configuration from environment variables."""
    config = EmbeddingConfig(
        name="embedding-service",
        version=os.environ.get("SERVICE_VERSION", "1.0.0"),
        environment=os.environ.get("ENV", "development"),
        debug=os.environ.get("EMBEDDING_DEBUG", "false").lower() == "true",
        host=os.environ.get("EMBEDDING_HOST", "0.0.0.0"),
        port=int(os.environ.get("EMBEDDING_PORT", "8000")),
        enable_cors=os.environ.get("EMBEDDING_ENABLE_CORS", "true").lower() == "true",
        cors_origins=os.environ.get("EMBEDDING_CORS_ORIGINS", "*").split(","),
        model_name=os.environ.get("EMBEDDING_MODEL", "all-minilm-l6-v2"),
        model_dimensions=int(os.environ.get("EMBEDDING_DIMENSIONS", "384")),
        model_cache_dir=os.environ.get("EMBEDDING_MODEL_CACHE_DIR", "/opt/models"),
        enable_model_caching=os.environ.get("EMBEDDING_ENABLE_MODEL_CACHING", "true").lower()
        == "true",
        batch_size=int(os.environ.get("EMBEDDING_BATCH_SIZE", "32")),
        openai_base_url=os.environ.get("LLMAAS_BASE_URL"),
        openai_api_key=resolve_secret("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        client_api_key=resolve_secret("EMBEDDING_SERVICE_CLIENT_API_KEY")
        or os.environ.get("EMBEDDING_SERVICE_CLIENT_API_KEY"),
        client_timeout_seconds=int(os.environ.get("EMBEDDING_CLIENT_TIMEOUT_SECONDS", "30")),
        client_max_retries=int(os.environ.get("EMBEDDING_CLIENT_MAX_RETRIES", "3")),
    )

    config_manager.register_config("embedding", config)
    return config


def load_retrieval_config() -> RetrievalConfig:
    """Load retrieval service configuration from environment variables."""
    config = RetrievalConfig(
        name="corpus-service",
        version=os.environ.get("SERVICE_VERSION", "v1"),
        environment=os.environ.get("ENV", "development"),
        debug=os.environ.get("CORPUS_DEBUG", "false").lower() == "true",
        host=os.environ.get("CORPUS_HOST", "0.0.0.0"),
        port=int(os.environ.get("CORPUS_PORT", "8001")),
        enable_cors=os.environ.get("CORPUS_ENABLE_CORS", "true").lower() == "true",
        cors_origins=os.environ.get("CORPUS_CORS_ORIGINS", "*").split(","),
        embedding_service_url=os.environ.get(
            "EMBEDDING_SERVICE_URL", "http://embedding-service:8000"
        ),
        embedding_service_token=resolve_secret("CORPUS_EMBEDDING_SERVICE_TOKEN")
        or os.environ.get("CORPUS_EMBEDDING_SERVICE_TOKEN"),
        documents_path=os.environ.get("CORPUS_DOCUMENTS_PATH", "/data/documents"),
        temp_path=os.environ.get("CORPUS_TEMP_PATH", "/data/tmp"),
        chunk_size=int(os.environ.get("CORPUS_CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.environ.get("CORPUS_CHUNK_OVERLAP", "200")),
        max_chunks_per_document=int(os.environ.get("CORPUS_MAX_CHUNKS_PER_DOCUMENT", "1000")),
    )

    config_manager.register_config("retrieval", config)
    return config


def load_orchestrator_config() -> OrchestratorConfig:
    """Load orchestrator service configuration from environment variables."""
    config = OrchestratorConfig(
        name="orchestrator-api",
        version=os.environ.get("SERVICE_VERSION", "1.0.0"),
        environment=os.environ.get("ENV", "development"),
        debug=os.environ.get("ORCHESTRATOR_DEBUG", "false").lower() == "true",
        host=os.environ.get("ORCHESTRATOR_HOST", "0.0.0.0"),
        port=int(os.environ.get("ORCHESTRATOR_PORT", "8000")),
        enable_cors=os.environ.get("ORCHESTRATOR_ENABLE_CORS", "true").lower() == "true",
        cors_origins=os.environ.get("ORCHESTRATOR_CORS_ORIGINS", "*").split(","),
        retrieval_service_url=os.environ.get("CORPUS_SVC_URL", "http://corpus-service:8001/api/v1"),
        embedding_service_url=os.environ.get(
            "EMBEDDING_SERVICE_URL", "http://embedding-service:8000"
        ),
        llm_guard_service_url=os.environ.get("LLM_GUARD_SERVICE_URL", "http://llm-guard-svc:8081"),
        llm_guard_enabled=os.environ.get("LLM_GUARD_ENABLED", "false").lower()
        in ("true", "1", "t"),
        llm_guard_timeout_seconds=float(os.environ.get("LLM_GUARD_TIMEOUT", "10.0")),
        inference_gateway_url=os.environ.get(
            "INFERENCE_GATEWAY_URL", "http://inference-gateway:8002"
        ),
        retrieval_enabled=os.environ.get("RETRIEVAL_ENABLED", "true").lower() in ("true", "1", "t"),
        request_timeout_seconds=(
            int(request_timeout) if (request_timeout := os.environ.get("REQUEST_TIMEOUT")) else None
        ),
        transcript_storage_enabled=os.environ.get("ENABLE_TRANSCRIPT_STORAGE", "false").lower()
        in ("true", "1", "t"),
        dashboard_health_endpoints=_load_dashboard_health_endpoints(),
        tool_secrets_key=resolve_secret("TOOL_SECRETS_KEY") or os.environ.get("TOOL_SECRETS_KEY"),
        pricing_default_input_per_million=float(
            os.environ.get("PRICING_DEFAULT_INPUT_PER_MILLION", "0.0")
        ),
        pricing_default_output_per_million=float(
            os.environ.get("PRICING_DEFAULT_OUTPUT_PER_MILLION", "0.0")
        ),
    )

    config_manager.register_config("orchestrator", config)
    return config


def load_llm_guard_config() -> LLMGuardConfig:
    """Load LLM Guard service configuration from environment variables."""
    config = LLMGuardConfig(
        name="llm-guard-svc",
        version=os.environ.get("SERVICE_VERSION", "1.0.0"),
        environment=os.environ.get("ENV", "development"),
        debug=os.environ.get("LLM_GUARD_DEBUG", "false").lower() == "true",
        host=os.environ.get("LLM_GUARD_HOST", "0.0.0.0"),
        port=int(os.environ.get("LLM_GUARD_PORT", "8081")),
        enable_cors=os.environ.get("LLM_GUARD_ENABLE_CORS", "true").lower() == "true",
        cors_origins=os.environ.get("LLM_GUARD_CORS_ORIGINS", "*").split(","),
        enabled=os.environ.get("LLM_GUARD_ENABLED", "false").lower() == "true",
        fail_fast=os.environ.get("LLM_GUARD_FAIL_FAST", "false").lower() == "true",
        cache_enabled=os.environ.get("LLM_GUARD_CACHE_ENABLED", "true").lower() == "true",
        cache_max_size=int(os.environ.get("LLM_GUARD_CACHE_MAX_SIZE", "1000")),
        cache_ttl_seconds=int(os.environ.get("LLM_GUARD_CACHE_TTL_SECONDS", "3600")),
        models_path=os.environ.get("LLM_GUARD_MODELS_PATH", "/app/models"),
        pii_model_dir=os.environ.get(
            "LLM_GUARD_PII_MODEL_DIR", "distilbert_finetuned_ai4privacy_v2"
        ),
        gibberish_model_dir=os.environ.get(
            "LLM_GUARD_GIBBERISH_MODEL_DIR",
            "madhurjindal-autonlp-Gibberish-Detector-492513457",
        ),
        language_model_dir=os.environ.get(
            "LLM_GUARD_LANGUAGE_MODEL_DIR",
            "protectai-xlm-roberta-base-language-detection-onnx",
        ),
        prompt_injection_model_dir=os.environ.get(
            "LLM_GUARD_PROMPT_INJECTION_MODEL_DIR",
            "protectai-deberta-v3-small-prompt-injection-v2",
        ),
        gliner_model_dir=os.environ.get("LLM_GUARD_GLINER_MODEL_DIR", "gliner_multi_pii-v1"),
        pii_score_threshold=float(os.environ.get("LLM_GUARD_PII_SCORE_THRESHOLD", "0.3")),
        pii_gliner_threshold=float(os.environ.get("LLM_GUARD_PII_GLINER_THRESHOLD", "0.93")),
    )

    config_manager.register_config("llm_guard", config)
    return config


def load_inference_gateway_config() -> InferenceGatewayConfig:
    """Load inference gateway configuration from environment variables."""

    redis_config = RedisConfig(
        url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        enabled=os.environ.get("REDIS_ENABLED", "true").lower() in ("true", "1", "t"),
        max_connections=int(os.environ.get("REDIS_MAX_CONNECTIONS", "50")),
        socket_timeout=int(os.environ.get("REDIS_SOCKET_TIMEOUT", "5")),
        socket_connect_timeout=int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
    )

    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=int(os.environ.get("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3")),
        timeout_seconds=int(os.environ.get("CIRCUIT_BREAKER_TIMEOUT_SECONDS", "60")),
        success_threshold=int(os.environ.get("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", "1")),
    )

    rate_limiter_config = RateLimiterConfig(
        enabled=os.environ.get("GATEWAY_RATE_LIMITING_ENABLED", "true").lower()
        in ("true", "1", "t"),
    )

    usage_logger_config = UsageLoggerConfig(
        batch_size=int(os.environ.get("GATEWAY_USAGE_BATCH_SIZE", "10")),
        flush_interval_seconds=float(os.environ.get("GATEWAY_USAGE_FLUSH_INTERVAL", "5.0")),
    )

    config = InferenceGatewayConfig(
        name="inference-gateway",
        version=os.environ.get("SERVICE_VERSION", "0.1.0"),
        environment=os.environ.get("ENV", "development"),
        debug=os.environ.get("GATEWAY_DEBUG", "false").lower() == "true",
        host=os.environ.get("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.environ.get("GATEWAY_PORT", "8002")),
        enable_cors=os.environ.get("GATEWAY_ENABLE_CORS", "true").lower() in ("true", "1", "t"),
        cors_origins=os.environ.get("GATEWAY_CORS_ORIGINS", "*").split(","),
        redis=redis_config,
        circuit_breaker=circuit_breaker_config,
        rate_limiter=rate_limiter_config,
        usage_logger=usage_logger_config,
    )

    config_manager.register_config("inference_gateway", config)
    return config


def _load_dashboard_health_endpoints() -> dict[str, str]:
    """Load dashboard health endpoints JSON (if configured)."""
    raw_value = os.environ.get("DASHBOARD_HEALTH_ENDPOINTS")
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed, dict):
        return {str(key): str(value) for key, value in parsed.items()}

    return {}


def load_all_configs() -> dict[str, BaseConfig]:
    """Load all service configurations."""
    load_database_config()
    load_qdrant_config()
    load_jwt_config()
    load_logging_config()
    load_opentelemetry_config()
    load_embedding_config()
    load_retrieval_config()
    load_orchestrator_config()
    load_llm_guard_config()
    load_inference_gateway_config()

    return config_manager.get_all_configs()


def get_config(config_type: str) -> BaseConfig | None:
    """Get a specific configuration by type."""
    return config_manager.get_config(config_type)


def validate_all_configs() -> bool:
    """Validate all loaded configurations."""
    return config_manager.validate_all()
