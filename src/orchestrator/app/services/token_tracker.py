"""
Token Tracker Service

Service for recording and aggregating LLM token usage.

P5-A23 Phase 7: Converted to async database patterns (Nov 2025).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.models import User
from shared.logging_utils.fastapi import get_logger

from ..db.models import TokenUsage
from ..schemas.token_usage import (
    AllCentersUsageSummaryResponse,
    TokenUsageResponse,
    TokenUsageSummary,
)

logger = get_logger(__name__)


class TokenTracker:
    """Service for tracking token usage"""

    def __init__(self, db: AsyncSession):
        """
        Initialize token tracker

        Args:
            db: Async database session
        """
        self.db = db

    async def record_usage(
        self,
        run_id: str,
        user_id: UUID,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        request_id: str | None = None,
        use_case_id: UUID | None = None,
        use_case_name: str | None = None,
        intent_type: str | None = None,
        model_provider: str | None = None,
        model_version: str | None = None,
        request_type: str | None = None,
        streaming_used: bool = False,
        call_duration_ms: int | None = None,
        cost_per_1k_in: Decimal | None = None,
        cost_per_1k_out: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TokenUsageResponse:
        """
        Record token usage for a request

        Args:
            run_id: Unique run identifier
            user_id: User who made the request
            model_id: Model identifier
            tokens_in: Input tokens
            tokens_out: Output tokens
            request_id: Request identifier
            use_case_id: Use case ID
            use_case_name: Use case name
            intent_type: Intent type
            model_provider: Model provider
            model_version: Model version
            request_type: Request type
            streaming_used: Whether streaming was used
            call_duration_ms: Call duration in milliseconds
            cost_per_1k_in: Cost per 1k input tokens
            cost_per_1k_out: Cost per 1k output tokens
            metadata: Additional metadata

        Returns:
            Created token usage record
        """
        try:
            # Get user's center_id
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            center_id = user.center_id if user else None

            # Calculate total cost if pricing is available
            total_cost = None
            if cost_per_1k_in is not None and cost_per_1k_out is not None:
                total_cost = (tokens_in * cost_per_1k_in / Decimal("1000.0")) + (
                    tokens_out * cost_per_1k_out / Decimal("1000.0")
                )

            # Create token usage record
            usage = TokenUsage(
                run_id=run_id,
                request_id=request_id,
                user_id=user_id,
                center_id=center_id,
                use_case_id=use_case_id,
                use_case_name=use_case_name,
                intent_type=intent_type,
                model_id=model_id,
                model_provider=model_provider,
                model_version=model_version,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                total_tokens=tokens_in + tokens_out,
                cost_per_1k_in=cost_per_1k_in,
                cost_per_1k_out=cost_per_1k_out,
                total_cost=total_cost,
                request_type=request_type,
                streaming_used=streaming_used,
                call_duration_ms=call_duration_ms,
                metadata=metadata or {},
            )

            self.db.add(usage)
            await self.db.commit()
            await self.db.refresh(usage)

            logger.info(
                f"Recorded token usage: run_id={run_id}, model={model_id}, "
                f"tokens={usage.total_tokens}",
                extra={
                    "run_id": run_id,
                    "user_id": str(user_id),
                    "model_id": model_id,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "total_tokens": usage.total_tokens,
                },
            )

            return TokenUsageResponse.model_validate(usage)

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to record token usage: {e}",
                extra={"run_id": run_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def get_center_usage_summary(
        self,
        center_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TokenUsageSummary:
        """
        Get usage summary for a specific center

        Args:
            center_id: Center identifier
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Token usage summary
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now(UTC)

        try:
            # Build query
            stmt = select(
                func.count().label("total_requests"),  # type: ignore[misc,call-arg]
                func.count(func.distinct(TokenUsage.user_id)).label("unique_users"),  # type: ignore[misc,call-arg]
                func.sum(TokenUsage.tokens_in).label("total_tokens_in"),
                func.sum(TokenUsage.tokens_out).label("total_tokens_out"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.total_cost).label("total_cost"),
                func.avg(TokenUsage.total_tokens).label("avg_tokens_per_request"),
            ).where(
                and_(
                    TokenUsage.center_id == center_id,
                    TokenUsage.created_at >= start_date,
                    TokenUsage.created_at <= end_date,
                )
            )

            result = await self.db.execute(stmt)
            row = result.first()

            # Handle None result
            if not row:
                return TokenUsageSummary(
                    center_id=center_id,
                    user_id=None,
                    total_requests=0,
                    unique_users=0,
                    total_tokens_in=0,
                    total_tokens_out=0,
                    total_tokens=0,
                    total_cost=None,
                    avg_tokens_per_request=None,
                    top_models=None,
                )

            # Get top models
            top_models_stmt = (
                select(
                    TokenUsage.model_id,
                    func.count().label("count"),  # type: ignore[misc,call-arg]
                )
                .where(
                    and_(
                        TokenUsage.center_id == center_id,
                        TokenUsage.created_at >= start_date,
                        TokenUsage.created_at <= end_date,
                    )
                )
                .group_by(TokenUsage.model_id)
                .order_by(func.count().desc())  # type: ignore[misc,call-arg]
                .limit(10)
            )

            top_models_result = await self.db.execute(top_models_stmt)
            top_models = {
                row.model_id: int(row.count)  # type: ignore[attr-defined,call-overload]
                for row in top_models_result.all()
            }

            return TokenUsageSummary(
                center_id=center_id,
                user_id=None,
                total_requests=row.total_requests or 0,
                unique_users=row.unique_users or 0,
                total_tokens_in=row.total_tokens_in or 0,
                total_tokens_out=row.total_tokens_out or 0,
                total_tokens=row.total_tokens or 0,
                total_cost=row.total_cost,
                avg_tokens_per_request=row.avg_tokens_per_request,
                top_models=top_models if top_models else None,
            )

        except Exception as e:
            logger.error(
                f"Failed to get center usage summary: {e}",
                extra={"center_id": center_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def get_all_centers_usage_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AllCentersUsageSummaryResponse:
        """
        Get usage summary for all centers

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Usage summary for all centers
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now(UTC)

        try:
            # Get per-center summaries
            stmt = (
                select(
                    TokenUsage.center_id,
                    func.count().label("total_requests"),  # type: ignore[misc,call-arg]
                    func.count(func.distinct(TokenUsage.user_id)).label("unique_users"),  # type: ignore[misc,call-arg]
                    func.sum(TokenUsage.tokens_in).label("total_tokens_in"),
                    func.sum(TokenUsage.tokens_out).label("total_tokens_out"),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.sum(TokenUsage.total_cost).label("total_cost"),
                    func.avg(TokenUsage.total_tokens).label("avg_tokens_per_request"),
                )
                .where(
                    and_(
                        TokenUsage.created_at >= start_date,
                        TokenUsage.created_at <= end_date,
                        TokenUsage.center_id.isnot(None),
                    )
                )
                .group_by(TokenUsage.center_id)
                .order_by(func.sum(TokenUsage.total_tokens).desc())
            )

            result = await self.db.execute(stmt)
            centers = []
            for row in result.all():
                centers.append(
                    TokenUsageSummary(
                        center_id=row.center_id,
                        user_id=None,
                        total_requests=row.total_requests or 0,
                        unique_users=row.unique_users or 0,
                        total_tokens_in=row.total_tokens_in or 0,
                        total_tokens_out=row.total_tokens_out or 0,
                        total_tokens=row.total_tokens or 0,
                        total_cost=row.total_cost,
                        avg_tokens_per_request=row.avg_tokens_per_request,
                        top_models=None,
                    )
                )

            # Calculate grand total
            grand_total_stmt = select(
                func.count().label("total_requests"),  # type: ignore[misc,call-arg]
                func.count(func.distinct(TokenUsage.user_id)).label("unique_users"),  # type: ignore[misc,call-arg]
                func.sum(TokenUsage.tokens_in).label("total_tokens_in"),
                func.sum(TokenUsage.tokens_out).label("total_tokens_out"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.total_cost).label("total_cost"),
                func.avg(TokenUsage.total_tokens).label("avg_tokens_per_request"),
            ).where(
                and_(
                    TokenUsage.created_at >= start_date,
                    TokenUsage.created_at <= end_date,
                )
            )

            grand_total_result = await self.db.execute(grand_total_stmt)
            grand_total_row = grand_total_result.first()

            if not grand_total_row:
                grand_total = TokenUsageSummary(
                    center_id=None,
                    user_id=None,
                    total_requests=0,
                    unique_users=0,
                    total_tokens_in=0,
                    total_tokens_out=0,
                    total_tokens=0,
                    total_cost=None,
                    avg_tokens_per_request=None,
                    top_models=None,
                )
            else:
                grand_total = TokenUsageSummary(
                    center_id=None,
                    user_id=None,
                    total_requests=grand_total_row.total_requests or 0,
                    unique_users=grand_total_row.unique_users or 0,
                    total_tokens_in=grand_total_row.total_tokens_in or 0,
                    total_tokens_out=grand_total_row.total_tokens_out or 0,
                    total_tokens=grand_total_row.total_tokens or 0,
                    total_cost=grand_total_row.total_cost,
                    avg_tokens_per_request=grand_total_row.avg_tokens_per_request,
                    top_models=None,
                )

            return AllCentersUsageSummaryResponse(
                start_date=start_date,
                end_date=end_date,
                centers=centers,
                grand_total=grand_total,
            )

        except Exception as e:
            logger.error(
                f"Failed to get all centers usage summary: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def get_user_usage_summary(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TokenUsageSummary:
        """
        Get usage summary for a specific user

        Args:
            user_id: User identifier
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)

        Returns:
            Token usage summary
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now(UTC)

        try:
            stmt = select(
                func.count().label("total_requests"),  # type: ignore[misc,call-arg]
                func.sum(TokenUsage.tokens_in).label("total_tokens_in"),
                func.sum(TokenUsage.tokens_out).label("total_tokens_out"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.total_cost).label("total_cost"),
                func.avg(TokenUsage.total_tokens).label("avg_tokens_per_request"),
            ).where(
                and_(
                    TokenUsage.user_id == user_id,
                    TokenUsage.created_at >= start_date,
                    TokenUsage.created_at <= end_date,
                )
            )

            result = await self.db.execute(stmt)
            row = result.first()

            if not row:
                return TokenUsageSummary(
                    center_id=None,
                    user_id=user_id,
                    total_requests=0,
                    unique_users=0,
                    total_tokens_in=0,
                    total_tokens_out=0,
                    total_tokens=0,
                    total_cost=None,
                    avg_tokens_per_request=None,
                    top_models=None,
                )

            return TokenUsageSummary(
                center_id=None,
                user_id=user_id,
                total_requests=row.total_requests or 0,
                unique_users=0,
                total_tokens_in=row.total_tokens_in or 0,
                total_tokens_out=row.total_tokens_out or 0,
                total_tokens=row.total_tokens or 0,
                total_cost=row.total_cost,
                avg_tokens_per_request=row.avg_tokens_per_request,
                top_models=None,
            )

        except Exception as e:
            logger.error(
                f"Failed to get user usage summary: {e}",
                extra={"user_id": str(user_id), "error": str(e)},
                exc_info=True,
            )
            raise
