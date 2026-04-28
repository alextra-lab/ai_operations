"""
Run manifest schemas for stateless telemetry (ADR-030).

These schemas define PII-free telemetry data without conversation content.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResultKind(str, Enum):
    """Enum for run result classification."""

    SUCCESS = "success"
    CONTRACT_VIOLATION = "contract_violation"
    POLICY_BLOCK = "policy_block"
    ERROR = "error"


class RunManifestCreate(BaseModel):
    """Request schema for creating a run manifest."""

    run_id: UUID
    use_case_id: str
    template_ver: str
    model_name: str
    model_version: str
    generation_params: dict[str, Any]
    schema_valid: bool
    conformance: float = Field(ge=0.0, le=1.0)
    tool_chain: list[str]
    idempotence_ok: bool
    latency_total_ms: int = Field(ge=0)
    latency_llm_ms: int = Field(ge=0)
    latency_tools_ms: int = Field(ge=0)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    result_kind: ResultKind

    @property
    def params_hash(self) -> str:
        """Generate deterministic hash of generation parameters."""
        params_json = json.dumps(self.generation_params, sort_keys=True)
        return hashlib.sha256(params_json.encode()).hexdigest()[:16]

    @field_validator("result_kind", mode="before")
    @classmethod
    def validate_result_kind(cls, v: str | ResultKind) -> ResultKind:
        """Validate and convert result_kind."""
        if isinstance(v, ResultKind):
            return v
        if isinstance(v, str):
            try:
                return ResultKind(v)
            except ValueError:
                valid_kinds = [k.value for k in ResultKind]
                raise ValueError(f"result_kind must be one of {valid_kinds}")
        raise ValueError("result_kind must be string or ResultKind")


class RunManifest(BaseModel):
    """Run manifest database model response."""

    run_id: UUID
    ts_utc: datetime
    use_case_id: str
    template_ver: str
    model_name: str
    model_version: str
    params_hash: str
    schema_valid: bool
    conformance: float
    tool_chain: list[str]
    idempotence_ok: bool
    latency_total_ms: int
    latency_llm_ms: int
    latency_tools_ms: int
    tokens_in: int
    tokens_out: int
    result_kind: ResultKind
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Alias for backwards compatibility
RunManifestResponse = RunManifest


class RunManifestQuery(BaseModel):
    """Query filters for run manifests."""

    use_case_id: str | None = None
    result_kind: ResultKind | None = None
    model_name: str | None = None
    min_conformance: float | None = Field(default=None, ge=0.0, le=1.0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    max_latency_ms: int | None = Field(default=None, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class RunManifestUpdate(BaseModel):
    """Schema for updating run manifest fields."""

    schema_valid: bool | None = None
    conformance: float | None = Field(default=None, ge=0.0, le=1.0)
    result_kind: ResultKind | None = None


class RunManifestStats(BaseModel):
    """Statistics for run manifests."""

    total_runs: int
    success_rate: float
    avg_latency_ms: float
    avg_conformance: float
    total_tokens: int
    error_count: int
    policy_block_count: int
    contract_violation_count: int


class RunManifestSummary(BaseModel):
    """Summary of run manifest data by use case."""

    use_case_id: str
    total_runs: int
    success_runs: int
    avg_latency_ms: float
    avg_conformance: float
    last_run_at: datetime
    result_kind_counts: dict[str, int]


class UseCaseMetricsResponse(BaseModel):
    """Aggregated metrics for a use case."""

    use_case_id: str
    total_runs: int
    avg_conformance: float
    avg_latency_ms: int
    avg_tokens_in: int
    avg_tokens_out: int
    success_count: int
    error_count: int
    schema_valid_count: int
    success_rate: float


class ExportRequest(BaseModel):
    """Request schema for exporting conversation from client."""

    conversation_id: str
    export_timestamp: datetime
    use_case: dict[str, Any]
    messages: list[dict[str, Any]]
    session_metadata: dict[str, Any] = Field(default_factory=dict)
    format: str = Field(default="json", pattern="^(json|markdown)$")


class ExportResponse(BaseModel):
    """Response schema for export."""

    export_id: str
    format: str
    content: str | None = None
    download_url: str | None = None


class SummaryRequest(BaseModel):
    """Request schema for generating summary from exported conversation."""

    messages: list[dict[str, Any]]
    use_case_context: dict[str, Any] = Field(default_factory=dict)
    summary_type: str = Field(default="executive", pattern="^(executive|technical|brief)$")


class SummaryResponse(BaseModel):
    """Response schema for generated summary."""

    summary: str
    key_points: list[str]
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
