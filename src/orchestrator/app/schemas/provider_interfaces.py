"""
Provider Interface Schemas for Stateless Core v1

This module defines Pydantic schemas for provider interfaces used in the
stateless architecture (ADR-033).

Providers are pluggable components for:
- History: Conversation history persistence
- Evidence: Evidence storage and retrieval
- Crypto: Cryptographic operations

For v1, all providers are no-op implementations that don't store data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Protocol
from uuid import UUID

from pydantic import BaseModel, Field


class HistoryProvider(Protocol):
    """Protocol for history persistence providers."""

    async def append(self, run_id: UUID, payload: dict[str, Any]) -> None:
        """Append history entry."""

    async def fetch(
        self, _case_id: str | None = None, _run_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Fetch history entries."""
        return []


class EvidenceSink(Protocol):
    """Protocol for evidence storage providers."""

    async def store(self, _evidence: dict[str, Any]) -> str:
        """Store evidence, return ID."""
        return ""

    async def retrieve(self, _evidence_id: str) -> dict[str, Any]:
        """Retrieve evidence by ID."""
        return {}


class CryptoProvider(Protocol):
    """Protocol for cryptographic operation providers."""

    async def encrypt(self, data: str) -> str:
        """Encrypt data."""
        return data

    async def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        return encrypted_data


class ProviderType(str, Enum):
    """Types of providers."""

    NONE = "none"
    GOVERNED = "governed"


class ProviderConfig(BaseModel):
    """Configuration for a provider."""

    provider_type: ProviderType = Field(..., description="Type of provider")
    enabled: bool = Field(True, description="Whether the provider is enabled")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific configuration"
    )
    timeout_seconds: int = Field(30, ge=1, le=300, description="Provider timeout in seconds")
    retry_attempts: int = Field(3, ge=0, le=10, description="Number of retry attempts")
    retry_delay_ms: int = Field(
        1000, ge=100, le=10000, description="Delay between retries in milliseconds"
    )


class HistoryEntry(BaseModel):
    """Schema for a history entry."""

    run_id: UUID = Field(..., description="Run ID for this entry")
    case_id: str | None = Field(None, description="Use case ID")
    timestamp: datetime = Field(..., description="When this entry was created")
    entry_type: str = Field(..., description="Type of history entry")
    content: dict[str, Any] = Field(..., description="Entry content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat(), UUID: str}


class EvidenceEntry(BaseModel):
    """Schema for an evidence entry."""

    evidence_id: str = Field(..., description="Unique evidence identifier")
    evidence_type: str = Field(..., description="Type of evidence")
    content: dict[str, Any] = Field(..., description="Evidence content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Evidence metadata")
    created_at: datetime = Field(..., description="When this evidence was created")
    expires_at: datetime | None = Field(None, description="When this evidence expires")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


class CryptoOperation(BaseModel):
    """Schema for a cryptographic operation."""

    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: str = Field(..., description="Type of operation (encrypt/decrypt)")
    data_size: int = Field(..., ge=0, description="Size of data in bytes")
    algorithm: str = Field(..., description="Cryptographic algorithm used")
    key_id: str | None = Field(None, description="Key identifier used")
    timestamp: datetime = Field(..., description="When this operation was performed")
    success: bool = Field(..., description="Whether the operation succeeded")
    error_message: str | None = Field(None, description="Error message if operation failed")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


class ProviderStatus(BaseModel):
    """Schema for provider status."""

    provider_type: str = Field(..., description="Type of provider")
    enabled: bool = Field(..., description="Whether the provider is enabled")
    healthy: bool = Field(..., description="Whether the provider is healthy")
    last_check: datetime = Field(..., description="Last health check timestamp")
    error_count: int = Field(0, ge=0, description="Number of errors in the last hour")
    response_time_ms: int | None = Field(
        None, ge=0, description="Average response time in milliseconds"
    )
    error_message: str | None = Field(None, description="Last error message")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


class ProviderMetrics(BaseModel):
    """Schema for provider metrics."""

    provider_type: str = Field(..., description="Type of provider")
    total_operations: int = Field(0, ge=0, description="Total operations performed")
    successful_operations: int = Field(0, ge=0, description="Successful operations")
    failed_operations: int = Field(0, ge=0, description="Failed operations")
    avg_response_time_ms: float = Field(0.0, ge=0.0, description="Average response time")
    max_response_time_ms: int = Field(0, ge=0, description="Maximum response time")
    min_response_time_ms: int = Field(0, ge=0, description="Minimum response time")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Error rate (0-1)")
    last_operation_at: datetime | None = Field(None, description="Last operation timestamp")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


class ProviderHealthCheck(BaseModel):
    """Schema for provider health check."""

    provider_type: str = Field(..., description="Type of provider")
    healthy: bool = Field(..., description="Whether the provider is healthy")
    check_time: datetime = Field(..., description="When the check was performed")
    response_time_ms: int = Field(..., ge=0, description="Health check response time")
    error_message: str | None = Field(None, description="Error message if unhealthy")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional health details")

    class Config:
        """Pydantic configuration."""

        from_attributes: ClassVar[bool] = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}
