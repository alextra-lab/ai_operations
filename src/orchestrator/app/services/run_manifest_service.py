"""
Run Manifest Service for Stateless Core v1

This module implements the run manifest service for telemetry capture
and storage in the stateless architecture (ADR-030).

Run manifests store PII-free telemetry data without conversation content.
"""

import hashlib
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import RunManifest as RunManifestModel
from ..schemas.run_manifest import (
    RunManifest,
    RunManifestCreate,
    RunManifestQuery,
    RunManifestStats,
    RunManifestSummary,
    RunManifestUpdate,
)


class RunManifestService:
    """Service for managing run manifests and telemetry data."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the run manifest service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def create_manifest(self, manifest_data: RunManifestCreate) -> RunManifest:
        """
        Create a new run manifest.

        Args:
            manifest_data: Run manifest data to create

        Returns:
            Created run manifest
        """
        now = datetime.utcnow()
        run_id = uuid4()

        manifest = RunManifestModel(
            run_id=run_id,
            use_case_id=manifest_data.use_case_id,
            template_ver=manifest_data.template_ver,
            model_name=manifest_data.model_name,
            model_version=manifest_data.model_version,
            params_hash=manifest_data.params_hash,
            schema_valid=manifest_data.schema_valid,
            conformance=manifest_data.conformance,
            tool_chain=manifest_data.tool_chain,
            idempotence_ok=manifest_data.idempotence_ok,
            latency_total_ms=manifest_data.latency_total_ms,
            latency_llm_ms=manifest_data.latency_llm_ms,
            latency_tools_ms=manifest_data.latency_tools_ms,
            tokens_in=manifest_data.tokens_in,
            tokens_out=manifest_data.tokens_out,
            result_kind=manifest_data.result_kind,
            ts_utc=now,
            created_at=now,
            updated_at=now,
        )

        self.db_session.add(manifest)
        await self.db_session.commit()
        await self.db_session.refresh(manifest)

        return RunManifest.model_validate(manifest)

    async def get_manifest(self, run_id: UUID) -> RunManifest | None:
        """
        Get a run manifest by ID.

        Args:
            run_id: Run manifest ID

        Returns:
            Run manifest if found, None otherwise
        """
        result = await self.db_session.execute(
            select(RunManifestModel).where(RunManifestModel.run_id == run_id)
        )
        manifest = result.scalar_one_or_none()

        if manifest:
            return RunManifest.model_validate(manifest)
        return None

    async def update_manifest(
        self, run_id: UUID, update_data: RunManifestUpdate
    ) -> RunManifest | None:
        """
        Update a run manifest.

        Args:
            run_id: Run manifest ID
            update_data: Update data

        Returns:
            Updated run manifest if found, None otherwise
        """
        result = await self.db_session.execute(
            select(RunManifestModel).where(RunManifestModel.run_id == run_id)
        )
        manifest = result.scalar_one_or_none()

        if not manifest:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(manifest, field, value)

        manifest.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(manifest)

        return RunManifest.model_validate(manifest)

    async def query_manifests(self, query: RunManifestQuery) -> list[RunManifest]:
        """
        Query run manifests with filters.

        Args:
            query: Query parameters

        Returns:
            List of matching run manifests
        """
        stmt = select(RunManifestModel)

        # Apply filters
        if query.use_case_id:
            stmt = stmt.where(RunManifestModel.use_case_id == query.use_case_id)

        if query.result_kind:
            stmt = stmt.where(RunManifestModel.result_kind == query.result_kind)

        if query.start_date:
            stmt = stmt.where(RunManifestModel.ts_utc >= query.start_date)

        if query.end_date:
            stmt = stmt.where(RunManifestModel.ts_utc <= query.end_date)

        if query.min_conformance is not None:
            stmt = stmt.where(RunManifestModel.conformance >= query.min_conformance)

        if query.max_latency_ms is not None:
            stmt = stmt.where(RunManifestModel.latency_total_ms <= query.max_latency_ms)

        # Apply pagination
        stmt = stmt.order_by(desc(RunManifestModel.ts_utc))
        stmt = stmt.offset(query.offset).limit(query.limit)

        result = await self.db_session.execute(stmt)
        manifests = result.scalars().all()

        return [RunManifest.model_validate(manifest) for manifest in manifests]

    async def get_manifest_stats(self, use_case_id: str | None = None) -> RunManifestStats:
        """
        Get run manifest statistics.

        Args:
            use_case_id: Optional use case ID to filter by

        Returns:
            Run manifest statistics
        """
        stmt = select(RunManifestModel)

        if use_case_id:
            stmt = stmt.where(RunManifestModel.use_case_id == use_case_id)

        # Get total runs
        total_runs_result = await self.db_session.execute(
            select(func.count()).select_from(stmt.subquery())  # type: ignore[misc,call-arg]
        )
        total_runs = total_runs_result.scalar() or 0

        if total_runs == 0:
            return RunManifestStats(
                total_runs=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                avg_conformance=0.0,
                total_tokens=0,
                error_count=0,
                policy_block_count=0,
                contract_violation_count=0,
            )

        # Get success rate
        success_result = await self.db_session.execute(
            select(func.count())  # type: ignore[misc,call-arg]
            .select_from(stmt.subquery())
            .where(RunManifestModel.result_kind == "success")
        )
        success_count = success_result.scalar() or 0
        success_rate = success_count / total_runs

        # Get average latency
        latency_result = await self.db_session.execute(
            select(func.avg(RunManifestModel.latency_total_ms)).select_from(stmt.subquery())
        )
        avg_latency_ms = float(latency_result.scalar() or 0)

        # Get average conformance
        conformance_result = await self.db_session.execute(
            select(func.avg(RunManifestModel.conformance)).select_from(stmt.subquery())
        )
        avg_conformance = float(conformance_result.scalar() or 0)

        # Get total tokens
        tokens_result = await self.db_session.execute(
            select(func.sum(RunManifestModel.tokens_in + RunManifestModel.tokens_out)).select_from(
                stmt.subquery()
            )
        )
        total_tokens = tokens_result.scalar() or 0

        # Get error counts
        error_result = await self.db_session.execute(
            select(func.count())  # type: ignore[misc,call-arg]
            .select_from(stmt.subquery())
            .where(RunManifestModel.result_kind == "error")
        )
        error_count = error_result.scalar() or 0

        policy_block_result = await self.db_session.execute(
            select(func.count())  # type: ignore[misc,call-arg]
            .select_from(stmt.subquery())
            .where(RunManifestModel.result_kind == "policy_block")
        )
        policy_block_count = policy_block_result.scalar() or 0

        contract_violation_result = await self.db_session.execute(
            select(func.count())  # type: ignore[misc,call-arg]
            .select_from(stmt.subquery())
            .where(RunManifestModel.result_kind == "contract_violation")
        )
        contract_violation_count = contract_violation_result.scalar() or 0

        return RunManifestStats(
            total_runs=total_runs,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            avg_conformance=avg_conformance,
            total_tokens=total_tokens,
            error_count=error_count,
            policy_block_count=policy_block_count,
            contract_violation_count=contract_violation_count,
        )

    async def get_manifest_summaries(self, limit: int = 100) -> list[RunManifestSummary]:
        """
        Get run manifest summaries grouped by use case.

        Args:
            limit: Maximum number of summaries to return

        Returns:
            List of run manifest summaries
        """
        # Get summaries grouped by use case
        stmt = (
            select(
                RunManifestModel.use_case_id,
                func.count(RunManifestModel.run_id).label("total_runs"),  # type: ignore[misc,call-arg]
                func.count(RunManifestModel.run_id)  # type: ignore[misc,call-arg]
                .filter(RunManifestModel.result_kind == "success")
                .label("success_runs"),
                func.avg(RunManifestModel.latency_total_ms).label("avg_latency_ms"),
                func.avg(RunManifestModel.conformance).label("avg_conformance"),
                func.max(RunManifestModel.ts_utc).label("last_run_at"),
            )
            .group_by(RunManifestModel.use_case_id)
            .order_by(desc(func.max(RunManifestModel.ts_utc)))
            .limit(limit)
        )

        result = await self.db_session.execute(stmt)
        rows = result.all()

        summaries = []
        for row in rows:
            # Get result kind counts for this use case
            kind_counts = {}
            for result_kind in [
                "success",
                "error",
                "policy_block",
                "contract_violation",
            ]:
                count_result = await self.db_session.execute(
                    select(func.count())  # type: ignore[misc,call-arg]
                    .where(RunManifestModel.use_case_id == row.use_case_id)
                    .where(RunManifestModel.result_kind == result_kind)
                )
                kind_counts[result_kind] = count_result.scalar() or 0

            summary = RunManifestSummary(
                use_case_id=row.use_case_id,
                total_runs=row.total_runs,
                success_runs=row.success_runs,
                avg_latency_ms=float(row.avg_latency_ms or 0),
                avg_conformance=float(row.avg_conformance or 0),
                last_run_at=row.last_run_at,
                result_kind_counts=kind_counts,
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    def generate_params_hash(params: dict) -> str:
        """
        Generate a hash for generation parameters for idempotence.

        Args:
            params: Generation parameters dictionary

        Returns:
            Hash string for the parameters
        """
        # Sort parameters for consistent hashing
        sorted_params = sorted(params.items())
        params_str = str(sorted_params)
        return hashlib.sha256(params_str.encode()).hexdigest()[:16]

    @staticmethod
    def create_manifest_from_execution(
        use_case_id: str,
        template_ver: str,
        model_name: str,
        model_version: str,
        params: dict,
        schema_valid: bool,
        conformance: float,
        tool_chain: list[str],
        idempotence_ok: bool,
        latency_total_ms: int,
        latency_llm_ms: int,
        latency_tools_ms: int,
        tokens_in: int,
        tokens_out: int,
        result_kind: str,
    ) -> RunManifestCreate:
        """
        Create a run manifest from execution data.

        Args:
            use_case_id: Use case identifier
            template_ver: Template version
            model_name: Model name
            model_version: Model version
            params: Generation parameters
            schema_valid: Whether schema validation passed
            conformance: Conformance score
            tool_chain: List of tools used
            idempotence_ok: Whether execution was idempotent
            latency_total_ms: Total latency in milliseconds
            latency_llm_ms: LLM latency in milliseconds
            latency_tools_ms: Tools latency in milliseconds
            tokens_in: Input tokens
            tokens_out: Output tokens
            result_kind: Result classification

        Returns:
            Run manifest create schema
        """
        import uuid as uuid_lib

        from ..schemas.run_manifest import ResultKind

        # Convert string to ResultKind enum
        result_kind_enum = ResultKind(result_kind) if isinstance(result_kind, str) else result_kind

        return RunManifestCreate(
            run_id=uuid_lib.uuid4(),
            use_case_id=use_case_id,
            template_ver=template_ver,
            model_name=model_name,
            model_version=model_version,
            generation_params=params,
            schema_valid=schema_valid,
            conformance=conformance,
            tool_chain=tool_chain,
            idempotence_ok=idempotence_ok,
            latency_total_ms=latency_total_ms,
            latency_llm_ms=latency_llm_ms,
            latency_tools_ms=latency_tools_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            result_kind=result_kind_enum,
        )
