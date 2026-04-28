"""Unit tests for run manifest schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from app.schemas.run_manifest import (
    ResultKind,
    RunManifest,
    RunManifestCreate,
    RunManifestQuery,
    RunManifestStats,
    RunManifestSummary,
    RunManifestUpdate,
)


class TestResultKind:
    """Test ResultKind enum."""

    def test_result_kind_values(self) -> None:
        """Test that ResultKind has correct values."""
        assert ResultKind.SUCCESS == "success"
        assert ResultKind.CONTRACT_VIOLATION == "contract_violation"
        assert ResultKind.POLICY_BLOCK == "policy_block"
        assert ResultKind.ERROR == "error"


class TestRunManifestCreate:
    """Test RunManifestCreate schema."""

    def test_valid_manifest_create(self) -> None:
        """Test creating a valid manifest for creation."""
        from uuid import uuid4

        manifest = RunManifestCreate(
            run_id=uuid4(),
            use_case_id="test-case-1",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="4.0",
            generation_params={"temperature": 0.7},
            schema_valid=True,
            conformance=0.95,
            tool_chain=["tool1", "tool2"],
            idempotence_ok=True,
            latency_total_ms=1500,
            latency_llm_ms=1200,
            latency_tools_ms=300,
            tokens_in=1000,
            tokens_out=500,
            result_kind=ResultKind.SUCCESS,
        )

        assert manifest.use_case_id == "test-case-1"
        assert manifest.template_ver == "1.0.0"
        assert manifest.model_name == "gpt-4"
        assert manifest.model_version == "4.0"
        assert manifest.generation_params == {"temperature": 0.7}
        assert manifest.schema_valid is True
        assert manifest.conformance == 0.95
        assert manifest.tool_chain == ["tool1", "tool2"]
        assert manifest.idempotence_ok is True
        assert manifest.latency_total_ms == 1500
        assert manifest.latency_llm_ms == 1200
        assert manifest.latency_tools_ms == 300
        assert manifest.tokens_in == 1000
        assert manifest.tokens_out == 500
        assert manifest.result_kind == ResultKind.SUCCESS

    def test_params_hash_generation(self) -> None:
        """Test that params_hash is generated correctly."""
        from uuid import uuid4

        manifest = RunManifestCreate(
            run_id=uuid4(),
            use_case_id="test-case-1",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="4.0",
            generation_params={"temperature": 0.7, "top_p": 0.9},
            schema_valid=True,
            conformance=0.95,
            tool_chain=[],
            idempotence_ok=True,
            latency_total_ms=1500,
            latency_llm_ms=1200,
            latency_tools_ms=300,
            tokens_in=1000,
            tokens_out=500,
            result_kind=ResultKind.SUCCESS,
        )

        # Hash should be deterministic and 16 chars
        assert len(manifest.params_hash) == 16
        assert isinstance(manifest.params_hash, str)


class TestRunManifest:
    """Test RunManifest schema."""

    def test_complete_manifest(self) -> None:
        """Test creating a complete manifest."""
        run_id = uuid4()
        now = datetime.utcnow()

        manifest = RunManifest(
            run_id=run_id,
            ts_utc=now,
            created_at=now,
            updated_at=now,
            use_case_id="test-case-1",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="4.0",
            params_hash="abc123",
            schema_valid=True,
            conformance=0.95,
            tool_chain=["tool1"],
            idempotence_ok=True,
            latency_total_ms=1500,
            latency_llm_ms=1200,
            latency_tools_ms=300,
            tokens_in=1000,
            tokens_out=500,
            result_kind=ResultKind.SUCCESS,
        )

        assert manifest.run_id == run_id
        assert manifest.ts_utc == now
        assert manifest.created_at == now
        assert manifest.updated_at == now


class TestRunManifestUpdate:
    """Test RunManifestUpdate schema."""

    def test_partial_update(self) -> None:
        """Test partial update of manifest."""
        update = RunManifestUpdate(
            conformance=0.98,
            result_kind=ResultKind.SUCCESS,
        )

        assert update.conformance == 0.98
        assert update.result_kind == ResultKind.SUCCESS
        assert update.schema_valid is None

    def test_empty_update(self) -> None:
        """Test empty update."""
        update = RunManifestUpdate()

        assert update.conformance is None
        assert update.result_kind is None


class TestRunManifestQuery:
    """Test RunManifestQuery schema."""

    def test_basic_query(self) -> None:
        """Test basic query creation."""
        query = RunManifestQuery(
            use_case_id="test-case-1",
            result_kind=ResultKind.SUCCESS,
            limit=50,
            offset=0,
        )

        assert query.use_case_id == "test-case-1"
        assert query.result_kind == ResultKind.SUCCESS
        assert query.limit == 50
        assert query.offset == 0

    def test_date_range_validation(self) -> None:
        """Test date range validation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2023, 12, 31)  # Before start_date

        with pytest.raises(ValueError, match="end_date must be after start_date"):
            RunManifestQuery(
                start_date=start_date,
                end_date=end_date,
            )

    def test_valid_date_range(self) -> None:
        """Test valid date range."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        query = RunManifestQuery(
            start_date=start_date,
            end_date=end_date,
        )

        assert query.start_date == start_date
        assert query.end_date == end_date


class TestRunManifestStats:
    """Test RunManifestStats schema."""

    def test_stats_creation(self) -> None:
        """Test creating stats."""
        stats = RunManifestStats(
            total_runs=100,
            success_rate=0.95,
            avg_latency_ms=1500.0,
            avg_conformance=0.92,
            total_tokens=50000,
            error_count=5,
            policy_block_count=2,
            contract_violation_count=1,
        )

        assert stats.total_runs == 100
        assert stats.success_rate == 0.95
        assert stats.avg_latency_ms == 1500.0
        assert stats.avg_conformance == 0.92
        assert stats.total_tokens == 50000
        assert stats.error_count == 5
        assert stats.policy_block_count == 2
        assert stats.contract_violation_count == 1


class TestRunManifestSummary:
    """Test RunManifestSummary schema."""

    def test_summary_creation(self) -> None:
        """Test creating summary."""
        now = datetime.utcnow()
        summary = RunManifestSummary(
            use_case_id="test-case-1",
            total_runs=50,
            success_runs=45,
            avg_latency_ms=1200.0,
            avg_conformance=0.94,
            last_run_at=now,
            result_kind_counts={"success": 45, "error": 5},
        )

        assert summary.use_case_id == "test-case-1"
        assert summary.total_runs == 50
        assert summary.success_runs == 45
        assert summary.avg_latency_ms == 1200.0
        assert summary.avg_conformance == 0.94
        assert summary.last_run_at == now
        assert summary.result_kind_counts == {"success": 45, "error": 5}
