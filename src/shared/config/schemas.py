"""
Configuration schemas for all AI Operations Platform (AIOP) services.
"""

from pydantic import Field

from .base import BaseConfig


class DatabaseConfig(BaseConfig):
    """Database connection configuration."""

    user: str = Field(default="user", description="Database username")
    password: str = Field(default="password", description="Database password")
    host: str = Field(default="postgres-db", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="aio", description="Database name")
    ssl_mode: str | None = Field(default=None, description="SSL mode")
    max_connections: int = Field(default=20, description="Maximum database connections")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    pool_size: int = Field(default=10, description="SQLAlchemy connection pool size")
    max_overflow: int = Field(default=20, description="SQLAlchemy max overflow connections")
    pool_recycle: int = Field(default=3600, description="Pool recycle interval in seconds")
    pool_pre_ping: bool = Field(default=True, description="Enable SQLAlchemy pool pre-ping")

    def get_connection_string(self, async_driver: bool = True) -> str:
        """Get database connection string."""
        driver = "asyncpg" if async_driver else "psycopg"
        ssl_part = f"?sslmode={self.ssl_mode}" if self.ssl_mode else ""
        return f"postgresql+{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_part}"


class QdrantConfig(BaseConfig):
    """Qdrant vector database configuration."""

    host: str = Field(default="vector-db", description="Qdrant host")
    port: int = Field(default=6333, description="Qdrant port")
    url: str | None = Field(default=None, description="Qdrant URL (overrides host/port)")
    api_key: str | None = Field(default=None, description="Qdrant API key")
    prefer_grpc: bool = Field(default=False, description="Whether to prefer gRPC over HTTP")
    timeout: float = Field(default=10.0, description="Timeout for Qdrant operations in seconds")
    collection_name: str = Field(default="documents", description="Name of the main collection")
    vector_size: int = Field(default=384, description="Size of embedding vectors")
    distance: str = Field(default="COSINE", description="Distance function for similarity search")
    m: int = Field(default=16, description="Number of bi-directional links in HNSW graph")
    ef_construct: int = Field(default=100, description="Size of the dynamic list for ef_construct")
    ef_search: int = Field(default=128, description="Size of the dynamic list for ef_search")
    default_limit: int = Field(default=10, description="Default number of results to return")
    default_offset: int = Field(default=0, description="Default offset for pagination")
    indexing_threshold: int = Field(
        default=20000,
        description="Number of vectors before enabling HNSW indexing",
    )

    def get_url(self) -> str:
        """Get Qdrant URL."""
        if self.url:
            return self.url
        return f"http://{self.host}:{self.port}"


class JWTConfig(BaseConfig):
    """JWT authentication configuration."""

    secret: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    issuer: str = Field(default="ai-operations-platform", description="JWT issuer")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )


class LoggingConfig(BaseConfig):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")
    service_name: str = Field(default="unknown", description="Service name for logging")
    enable_structured_logging: bool = Field(default=True, description="Enable structured logging")
    enable_request_id: bool = Field(default=True, description="Enable request ID logging")
    verbose: bool = Field(default=False, description="Enable verbose request/response logging")
    redact_logs: bool = Field(default=False, description="Enable sensitive field redaction")
    redaction_level: str = Field(
        default="partial",
        description="Redaction level to apply (none|partial|full)",
    )


class OpenTelemetryConfig(BaseConfig):
    """OpenTelemetry configuration."""

    enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    endpoint: str | None = Field(default=None, description="OTLP endpoint")
    service_name: str = Field(default="aio", description="Service name for telemetry")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")


class ServiceConfig(BaseConfig):
    """Base service configuration."""

    name: str = Field(..., description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Service host")
    port: int = Field(default=8000, description="Service port")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    cors_origins: list[str] = Field(default=["*"], description="CORS origins")


class EmbeddingConfig(ServiceConfig):
    """Embedding service configuration."""

    model_name: str = Field(default="all-minilm-l6-v2", description="Default embedding model")
    model_dimensions: int = Field(default=384, description="Model dimensions")
    model_cache_dir: str = Field(default="/opt/models", description="Model cache directory")
    enable_model_caching: bool = Field(default=True, description="Enable model caching")
    batch_size: int = Field(default=32, description="Default batch size")
    openai_base_url: str | None = Field(default=None, description="OpenAI base URL")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    client_api_key: str | None = Field(
        default=None, description="Internal client API key for embedding service access"
    )
    client_timeout_seconds: int = Field(default=30, description="Client timeout in seconds")
    client_max_retries: int = Field(default=3, description="Maximum client retries")


class RetrievalConfig(ServiceConfig):
    """Retrieval service configuration."""

    embedding_service_url: str = Field(
        default="http://embedding-service:8000", description="Embedding service URL"
    )
    embedding_service_token: str | None = Field(default=None, description="Embedding service token")
    documents_path: str = Field(default="/data/documents", description="Documents storage path")
    temp_path: str = Field(default="/data/tmp", description="Temporary files path")
    chunk_size: int = Field(default=1000, description="Default chunk size")
    chunk_overlap: int = Field(default=200, description="Default chunk overlap")
    max_chunks_per_document: int = Field(default=1000, description="Maximum chunks per document")


class OrchestratorConfig(ServiceConfig):
    """Orchestrator service configuration."""

    retrieval_service_url: str = Field(
        default="http://corpus-service:8001/api/v1", description="Retrieval service URL"
    )
    embedding_service_url: str = Field(
        default="http://embedding-service:8000", description="Embedding service URL"
    )
    llm_guard_service_url: str = Field(
        default="http://llm-guard-svc:8081", description="LLM Guard service URL"
    )
    llm_guard_enabled: bool = Field(default=True, description="Enable LLM Guard integration")
    llm_guard_timeout_seconds: float = Field(default=10.0, description="LLM Guard timeout (s)")
    inference_gateway_url: str = Field(
        default="http://inference-gateway:8002", description="Inference gateway URL"
    )
    retrieval_enabled: bool = Field(default=True, description="Enable retrieval for requests")
    request_timeout_seconds: int | None = Field(
        default=None, description="Optional request timeout override for LLM router"
    )
    transcript_storage_enabled: bool = Field(
        default=False, description="Enable transcript storage for history endpoints"
    )
    dashboard_health_endpoints: dict[str, str] = Field(
        default_factory=dict, description="Service health endpoints for dashboard monitoring"
    )
    tool_secrets_key: str | None = Field(
        default=None, description="Encryption key for tool secrets storage"
    )
    pricing_default_input_per_million: float = Field(
        default=0.0, description="Fallback input pricing per million tokens"
    )
    pricing_default_output_per_million: float = Field(
        default=0.0, description="Fallback output pricing per million tokens"
    )


class RedisConfig(BaseConfig):
    """Redis cache configuration."""

    url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    enabled: bool = Field(default=True, description="Enable Redis-backed features")
    max_connections: int = Field(default=50, description="Maximum Redis connections")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout in seconds")


class CircuitBreakerConfig(BaseConfig):
    """Circuit breaker parameters."""

    failure_threshold: int = Field(default=3, description="Failures before opening circuit")
    timeout_seconds: int = Field(default=60, description="Seconds to stay open before half-open")
    success_threshold: int = Field(
        default=1, description="Number of successes to close the circuit"
    )


class RateLimiterConfig(BaseConfig):
    """Rate limiter configuration."""

    enabled: bool = Field(default=True, description="Enable gateway rate limiting")


class UsageLoggerConfig(BaseConfig):
    """Usage logger configuration."""

    batch_size: int = Field(default=10, description="Usage log batch size")
    flush_interval_seconds: float = Field(default=5.0, description="Flush interval in seconds")


class InferenceGatewayConfig(ServiceConfig):
    """Inference gateway service configuration."""

    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Circuit breaker settings"
    )
    rate_limiter: RateLimiterConfig = Field(
        default_factory=RateLimiterConfig, description="Rate limiter configuration"
    )
    usage_logger: UsageLoggerConfig = Field(
        default_factory=UsageLoggerConfig, description="Usage logger configuration"
    )


class LLMGuardConfig(ServiceConfig):
    """LLM Guard service configuration."""

    enabled: bool = Field(default=True, description="Enable LLM Guard")
    fail_fast: bool = Field(default=False, description="Fail fast on violations")
    cache_enabled: bool = Field(default=True, description="Enable result caching")
    cache_max_size: int = Field(default=1000, description="Maximum cache size")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    models_path: str = Field(default="/app/models", description="Models directory path")
    pii_model_dir: str = Field(
        default="distilbert_finetuned_ai4privacy_v2",
        description="PII detection model directory name within models_path",
    )
    gibberish_model_dir: str = Field(
        default="madhurjindal-autonlp-Gibberish-Detector-492513457",
        description="Gibberish detection model directory name within models_path",
    )
    language_model_dir: str = Field(
        default="protectai-xlm-roberta-base-language-detection-onnx",
        description="Language detection model directory name within models_path",
    )
    prompt_injection_model_dir: str = Field(
        default="protectai-deberta-v3-small-prompt-injection-v2",
        description="Prompt injection detection model directory name within models_path",
    )
