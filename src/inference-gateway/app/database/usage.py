"""
GatewayUsageLog SQLAlchemy model.

Maps to gateway_usage_log table created by migration 030.

VERIFICATION CRITICAL:
- Uses existing shared.db.connection.Base
- Follows existing model pattern (src/backend/app/db/models.py)
- Maps to table created by migration 030_gateway_usage_log.sql
"""

import uuid
from datetime import UTC, datetime

from shared.db.connection import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class GatewayUsageLog(Base):
    """
    Usage log record for Inference Gateway requests.

    Maps to gateway_usage_log table (migration 030).
    Tracks all Gateway requests for analytics, billing, and debugging.

    Attributes:
        id: Primary key (UUID)
        request_id: Correlation ID from X-Request-ID header
        ts_utc: Timestamp of request (UTC)
        user_id: User making request (nullable for service accounts)
        integration_id: Service account identifier (e.g., "orchestrator")
        endpoint: Gateway endpoint (e.g., "/v1/chat/completions")
        provider_id: Provider used for request
        provider_name: Denormalized provider name for fast queries
        model_requested: Model requested by client
        model_used: Actual model used (may differ after routing)
        tokens_in: Input tokens
        tokens_out: Output tokens
        cost_eur: Total cost in EUR
        latency_total_ms: Total request latency
        latency_gateway_ms: Gateway processing overhead
        latency_provider_ms: Provider API call latency
        http_status: HTTP status code returned
        success: Whether request succeeded
        error_type: Error classification if failed
        error_message: Error details (sanitized)
        stream_enabled: Whether streaming was used
        cache_hit: Cache hit (future use)
        retry_count: Number of retries attempted
        metadata_json: Additional request context
        created_at: Record creation timestamp
    """

    __tablename__ = "gateway_usage_log"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request correlation
    request_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ts_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
        index=True,
    )

    # Request metadata
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    integration_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)

    # Routing information
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gateway_providers.id"),
        nullable=True,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_requested: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Token usage
    tokens_in: Mapped[int] = mapped_column(
        Integer, CheckConstraint("tokens_in >= 0"), nullable=False, default=0
    )
    tokens_out: Mapped[int] = mapped_column(
        Integer, CheckConstraint("tokens_out >= 0"), nullable=False, default=0
    )
    # Note: tokens_total is a GENERATED column in the database

    # Cost tracking
    cost_eur: Mapped[float | None] = mapped_column(
        CheckConstraint("cost_eur >= 0"), nullable=True, default=0.0
    )

    # Latency metrics (milliseconds)
    latency_total_ms: Mapped[int] = mapped_column(
        Integer, CheckConstraint("latency_total_ms >= 0"), nullable=False
    )
    latency_gateway_ms: Mapped[int | None] = mapped_column(
        Integer, CheckConstraint("latency_gateway_ms >= 0"), nullable=True
    )
    latency_provider_ms: Mapped[int | None] = mapped_column(
        Integer, CheckConstraint("latency_provider_ms >= 0"), nullable=True
    )

    # Request/response status
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional context
    stream_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Record timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<GatewayUsageLog(id={self.id}, request_id={self.request_id}, "
            f"model={self.model_requested}, status={self.http_status})>"
        )
