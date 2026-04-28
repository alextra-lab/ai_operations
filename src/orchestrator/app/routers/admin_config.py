"""
Admin Configuration Router

API endpoints for system configuration management.
ADR-038: JSONB configuration storage.
ADR-039: RLS admin-only access.

P5-A11: Migrated to async database patterns (Nov 2025).
"""

from datetime import UTC, datetime
from typing import Any, cast

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import admin_required, get_current_user
from shared.auth.models import TokenPayload

from ..db.database import get_async_db
from ..schemas.system_config import (
    AuthConfig,
    ConfigExportResponse,
    ConfigImportRequest,
    ConfigImportResponse,
    ConfigSectionResponse,
    CorpusConfig,
    FeatureFlags,
    SystemConfig,
    SystemConfigFull,
)

router = APIRouter(prefix="/api/v1/admin/config", tags=["admin-config"])


# ============================================================================
# Configuration Schema Mapping
# ============================================================================

SECTION_SCHEMAS = {
    "corpus": CorpusConfig,
    "auth": AuthConfig,
    "features": FeatureFlags,
    "system": SystemConfig,
}


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/",
    response_model=SystemConfigFull,
    dependencies=[Depends(admin_required)],
    summary="Get all configuration",
    description="Retrieve all system configuration sections.",
)
async def get_config(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> SystemConfigFull:
    """Get all system configuration."""
    try:
        # Query all sections
        query = text("SELECT section, config FROM system_config ORDER BY section")
        result = await db.execute(query)
        rows = result.fetchall()

        # Build config dict
        config_data = {}
        for row in rows:
            section_name = row[0]
            section_config = row[1]
            config_data[section_name] = section_config

        # Validate and return
        return SystemConfigFull.model_validate(config_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {e!s}",
        ) from e


@router.get(
    "/{section}",
    response_model=ConfigSectionResponse,
    dependencies=[Depends(admin_required)],
    summary="Get configuration section",
    description="Retrieve specific configuration section.",
)
async def get_config_section(
    section: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ConfigSectionResponse:
    """Get specific configuration section."""
    if section not in SECTION_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid section: {section}. Must be one of: {list(SECTION_SCHEMAS.keys())}",
        )

    try:
        query = text(
            """
            SELECT config, updated_at, updated_by
            FROM system_config
            WHERE section = :section
            """
        )
        result = await db.execute(query, {"section": section})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration section '{section}' not found",
            )

        return ConfigSectionResponse(
            section=section,
            config=row[0],
            updated_at=row[1].isoformat() if row[1] else "",
            updated_by=str(row[2]) if row[2] else None,
            restart_required=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load section: {e!s}",
        )


@router.put(
    "/{section}",
    response_model=ConfigSectionResponse,
    dependencies=[Depends(admin_required)],
    summary="Update configuration section",
    description="Update configuration section with validation.",
)
async def update_config_section(
    section: str,
    config: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ConfigSectionResponse:
    """
    Update configuration section.

    Validates against schema before saving.
    Some settings require service restart.
    """
    if section not in SECTION_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid section: {section}. Must be one of: {list(SECTION_SCHEMAS.keys())}",
        )

    # Validate config against schema
    schema_class = SECTION_SCHEMAS[section]
    try:
        validated_config = schema_class.model_validate(config)  # type: ignore[attr-defined]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid configuration: {e!s}",
        )

    # Update database
    try:
        # Convert Pydantic model to JSON string for JSONB cast
        config_json = validated_config.model_dump_json()

        query = text(
            """
            UPDATE system_config
            SET config = CAST(:config AS jsonb),
                updated_by = CAST(:user_id AS uuid)
            WHERE section = :section
            RETURNING config, updated_at, updated_by
            """
        )
        result = await db.execute(
            query,
            {
                "section": section,
                "config": config_json,
                "user_id": str(current_user.user_id),
            },
        )
        row = result.fetchone()

        # Validate before commit - ensure UPDATE affected a row
        if not row or len(row) < 3:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration section '{section}' not found",
            )

        # Commit only after validation passes
        await db.commit()

        # Determine if restart required
        restart_required = section in ("system", "corpus")

        return ConfigSectionResponse(
            section=section,
            config=row[0],
            updated_at=row[1].isoformat() if row[1] else "",
            updated_by=str(row[2]) if row[2] else None,
            restart_required=restart_required,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {e!s}",
        )


@router.get(
    "/schema/{section}",
    dependencies=[Depends(admin_required)],
    summary="Get configuration schema",
    description="Get JSON schema for configuration section.",
)
async def get_config_schema(
    section: str,
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """Get JSON schema for configuration section."""
    if section not in SECTION_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid section: {section}. Must be one of: {list(SECTION_SCHEMAS.keys())}",
        )

    schema_class = SECTION_SCHEMAS[section]
    return cast(
        "dict[str, Any]",
        schema_class.model_json_schema(),  # type: ignore[attr-defined]
    )


@router.post(
    "/export",
    response_model=ConfigExportResponse,
    dependencies=[Depends(admin_required)],
    summary="Export configuration",
    description="Export all configuration as YAML.",
)
async def export_config(
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ConfigExportResponse:
    """Export all configuration as YAML."""
    try:
        # Get all config
        config = await get_config(db, current_user)

        # Convert to YAML
        config_dict = config.model_dump()
        config_yaml = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)

        return ConfigExportResponse(
            config_yaml=config_yaml,
            exported_at=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {e!s}",
        )


@router.post(
    "/import",
    response_model=ConfigImportResponse,
    dependencies=[Depends(admin_required)],
    summary="Import configuration",
    description="Import configuration from YAML with validation.",
)
async def import_config(
    request: ConfigImportRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> ConfigImportResponse:
    """
    Import configuration from YAML.

    Validates before applying.
    Set validate_only=true to check without saving.
    """
    try:
        # Parse YAML
        config_dict = yaml.safe_load(request.config_yaml)
        if not isinstance(config_dict, dict):
            raise ValueError("YAML must be a dictionary")

        # Validate full config
        validated_config = SystemConfigFull.model_validate(config_dict)

        # If validate_only, return success
        if request.validate_only:
            return ConfigImportResponse(
                success=True,
                sections_updated=[],
                restart_required=False,
            )

        # Update each section
        sections_updated = []
        for section_name in SECTION_SCHEMAS:
            section_config = getattr(validated_config, section_name)
            query = text(
                """
                UPDATE system_config
                SET config = :config::jsonb,
                    updated_by = :user_id::uuid
                WHERE section = :section
                """
            )
            await db.execute(
                query,
                {
                    "section": section_name,
                    "config": section_config.model_dump_json(),
                    "user_id": current_user.user_id,
                },
            )
            sections_updated.append(section_name)

        await db.commit()

        return ConfigImportResponse(
            success=True,
            sections_updated=sections_updated,
            restart_required=True,  # Safest assumption
        )

    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid YAML: {e!s}",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to import configuration: {e!s}",
        )
