"""
Prompt Pattern Library API Router.

Provides endpoints for browsing, searching, and applying reusable prompt patterns.
"""

import math
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from shared.logging_utils.fastapi import configure_logging

from ..db.database import get_async_db
from ..models.prompt_pattern import PromptPattern
from ..schemas.prompt_patterns import (
    ApplyPatternRequest,
    ApplyPatternResponse,
    FewShotExample,
    PromptPatternListResponse,
    PromptPatternResponse,
)

logger = configure_logging(service_name="prompt_patterns_router")
router = APIRouter(prefix="/api/v1/patterns", tags=["Prompt Patterns"])


@router.get("", response_model=PromptPatternListResponse)
async def list_patterns(
    category: str | None = Query(None, description="Filter by category (e.g., 'reasoning', 'rag')"),
    search: str | None = Query(None, description="Search in name, description, tags"),
    tags: list[str] = Query(default=[], description="Filter by tags (OR logic)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("use_count", description="Sort by: name, category, use_count, created_at"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> PromptPatternListResponse:
    """
    List and search prompt patterns with pagination.

    **Filters:**
    - category: Filter by pattern category
    - search: Search in name, description, and tags
    - tags: Filter by one or more tags (OR logic)

    **Sorting:**
    - name, category, use_count (most popular first), created_at (newest first)
    """
    logger.info(
        "Listing prompt patterns",
        extra={
            "user_id": str(current_user.user_id),
            "category": category,
            "search": search,
            "tags": tags,
            "page": page,
            "page_size": page_size,
        },
    )

    # Build query
    stmt = select(PromptPattern)

    # Apply filters
    filters = []
    if category:
        filters.append(PromptPattern.category == category)
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                PromptPattern.name.ilike(search_pattern),
                PromptPattern.description.ilike(search_pattern),
                func.jsonb_path_exists(
                    PromptPattern.tags, f'$[*] ? (@ like_regex "{search}" flag "i")'
                ),
            )
        )
    if tags:
        # OR logic: pattern must have at least one of the specified tags
        tag_conditions = [
            func.jsonb_path_exists(PromptPattern.tags, f'$[*] ? (@ == "{tag}")') for tag in tags
        ]
        filters.append(or_(*tag_conditions))

    if filters:
        stmt = stmt.where(and_(*filters))

    # Count total (separate query for count)
    count_stmt = select(func.count(PromptPattern.pattern_id))
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Apply sorting
    sort_column_map = {
        "name": PromptPattern.name,
        "category": PromptPattern.category,
        "use_count": PromptPattern.use_count,
        "created_at": PromptPattern.created_at,
    }
    sort_column = sort_column_map.get(sort_by, PromptPattern.use_count)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(stmt)
    patterns = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    logger.info(
        "Patterns listed",
        extra={
            "user_id": str(current_user.user_id),
            "total_found": total,
            "patterns_returned": len(patterns),
        },
    )

    return PromptPatternListResponse(
        patterns=[PromptPatternResponse.model_validate(p) for p in patterns],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{pattern_id}", response_model=PromptPatternResponse)
async def get_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> PromptPatternResponse:
    """
    Get detailed information about a specific prompt pattern.
    """
    logger.info(
        "Getting pattern detail",
        extra={"user_id": str(current_user.user_id), "pattern_id": pattern_id},
    )

    stmt = select(PromptPattern).where(PromptPattern.pattern_id == pattern_id)
    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{pattern_id}' not found",
        )

    return PromptPatternResponse.model_validate(pattern)


@router.post("/apply", response_model=ApplyPatternResponse)
async def apply_pattern(
    request: ApplyPatternRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ApplyPatternResponse:
    """
    Apply a pattern with variable substitutions.

    Returns rendered prompts with variables replaced by provided values.
    Variables in templates use double curly braces: {{variable_name}}

    **Example:**
    ```json
    {
        "pattern_id": "threat-analysis",
        "variables": {
            "domain": "threat intelligence",
            "framework": "MITRE ATT&CK"
        }
    }
    ```
    """
    logger.info(
        "Applying pattern",
        extra={
            "user_id": str(current_user.user_id),
            "pattern_id": request.pattern_id,
            "variables": list(request.variables.keys()),
        },
    )

    # Fetch pattern
    stmt = select(PromptPattern).where(PromptPattern.pattern_id == request.pattern_id)
    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern '{request.pattern_id}' not found",
        )

    # Substitute variables
    def substitute_variables(template: str | None, variables: dict[str, str]) -> str | None:
        """Replace {{variable_name}} with actual values."""
        if not template:
            return None

        result = template
        for key, value in variables.items():
            # Replace {{key}} with value
            pattern_regex = r"\{\{" + re.escape(key) + r"\}\}"
            result = re.sub(pattern_regex, value, result)

        return result

    # Apply substitutions
    system_prompt = substitute_variables(pattern.system_prompt_template, request.variables)
    developer_prompt = substitute_variables(pattern.developer_prompt_template, request.variables)

    # Process few-shots (substitute in both user and assistant texts)
    fewshots = []
    if pattern.fewshots_template:
        for example in pattern.fewshots_template:
            fewshots.append(
                FewShotExample(
                    user=substitute_variables(example.get("user", ""), request.variables) or "",
                    assistant=substitute_variables(example.get("assistant", ""), request.variables)
                    or "",
                )
            )

    # Increment use_count
    pattern.use_count += 1
    await db.commit()
    await db.refresh(pattern)

    logger.info(
        "Pattern applied successfully",
        extra={
            "user_id": str(current_user.user_id),
            "pattern_id": request.pattern_id,
            "use_count": pattern.use_count,
        },
    )

    return ApplyPatternResponse(
        system_prompt=system_prompt,
        developer_prompt=developer_prompt,
        fewshots=fewshots,
        pattern_used=pattern.pattern_id,
        variables_applied=request.variables,
    )
