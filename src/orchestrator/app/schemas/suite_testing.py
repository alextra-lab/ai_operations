"""
Test Suite schemas for corpus validation.

Supports BYOM (Bring Your Own Metrics) test suites with retrieval metrics.
ADR-034: Use Case Validation & Test Harness
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TestQuestionBase(BaseModel):
    """Base schema for test questions."""

    query: str = Field(..., min_length=1, description="Test query text")
    expected_doc_ids: list[UUID] = Field(
        default_factory=list, description="Expected document IDs in results"
    )
    expected_phrases: list[str] = Field(
        default_factory=list, description="Expected phrases in results"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    relevance_scores: dict[str, float] | None = Field(
        None,
        description="Map of doc_id (as string) to relevance score (0.0-1.0) for nDCG calculation",
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Query must not be empty")
        return v.strip()

    @field_validator("relevance_scores")
    @classmethod
    def relevance_scores_valid(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate relevance scores are in valid range."""
        if v is not None:
            for doc_id, score in v.items():
                if not 0.0 <= score <= 1.0:
                    raise ValueError(f"Relevance score for {doc_id} must be between 0.0 and 1.0")
        return v


class TestQuestionCreate(TestQuestionBase):
    """Schema for creating a test question."""

    suite_id: UUID = Field(..., description="Parent test suite ID")


class TestQuestion(TestQuestionBase):
    """Complete test question schema with database fields."""

    id: UUID
    suite_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TestSuiteBase(BaseModel):
    """Base schema for test suites."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique test suite name")
    description: str | None = Field(None, description="Test suite description")
    collection_ids: list[UUID] = Field(
        default=..., min_length=1, description="Collection IDs to test against"
    )
    k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of results to retrieve (for Hit@K, nDCG@K)",
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate name is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Name must not be empty")
        return v.strip()


class TestSuiteCreate(TestSuiteBase):
    """Schema for creating a test suite."""

    questions: list[TestQuestionBase] = Field(
        default_factory=list, description="Initial test questions"
    )


class TestSuiteUpdate(BaseModel):
    """Schema for updating a test suite."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    collection_ids: list[UUID] | None = Field(default=None, min_length=1)
    k: int | None = Field(None, ge=1, le=100)


class TestSuite(TestSuiteBase):
    """Complete test suite schema with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    questions: list[TestQuestion] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TestSuiteResultBase(BaseModel):
    """Base schema for test suite execution results."""

    suite_id: UUID
    chunking_strategy: str = Field(..., description="Chunking strategy used (e.g., fixed_token)")
    collection_id: UUID = Field(..., description="Collection ID tested")
    avg_hit_at_k: float = Field(..., ge=0.0, le=1.0, description="Average Hit@K across all queries")
    avg_mrr: float = Field(..., ge=0.0, le=1.0, description="Average MRR across all queries")
    avg_ndcg: float = Field(..., ge=0.0, le=1.0, description="Average nDCG@K across all queries")
    zero_result_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Percentage of queries with zero results"
    )
    total_queries: int = Field(..., ge=0, description="Total number of queries executed")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time in milliseconds")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TestSuiteResultCreate(TestSuiteResultBase):
    """Schema for creating a test suite result."""


class TestSuiteResult(TestSuiteResultBase):
    """Complete test suite result schema with database fields."""

    id: UUID
    executed_at: datetime

    class Config:
        from_attributes = True


class TestSuiteExecutionRequest(BaseModel):
    """Request schema for executing a test suite."""

    suite_id: UUID
    collection_id: UUID | None = Field(
        None, description="Specific collection to test (defaults to all in suite)"
    )
    chunking_strategy: str | None = Field(
        None, description="Specific chunking strategy to test (defaults to current)"
    )
    k: int | None = Field(None, ge=1, le=100, description="Override K value for this execution")


class TestSuiteExecutionResponse(BaseModel):
    """Response schema for test suite execution."""

    result: TestSuiteResult
    query_results: list[dict[str, Any]] = Field(
        ..., description="Individual query results with metrics"
    )
    summary: dict[str, Any] = Field(..., description="Execution summary and insights")


class TestSuiteYAMLExport(BaseModel):
    """Schema for YAML export format (BYOM)."""

    name: str
    description: str | None = None
    collection_ids: list[str]  # UUIDs as strings for YAML
    k: int = 5
    questions: list[dict[str, Any]] = Field(
        ...,
        description="Questions in simplified format for YAML",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "UC-Detect-Leaks",
                "description": "Validate retrieval for data leak detection",
                "collection_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
                "k": 5,
                "questions": [
                    {
                        "query": "What are allowed egress rules?",
                        "expected_doc_ids": ["doc-123", "doc-456"],
                        "expected_phrases": ["egress", "port 443 only"],
                        "tags": ["network", "policy"],
                    }
                ],
            }
        }
    }
