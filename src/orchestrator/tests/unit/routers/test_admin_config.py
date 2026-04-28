"""
Unit tests for Admin Configuration Router

Tests system configuration API endpoints.
P5-A11: Updated for async database patterns (Nov 2025).
"""

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi import HTTPException, status

from shared.auth.models import TokenPayload
from src.orchestrator.app.routers.admin_config import (
    export_config,
    get_config,
    get_config_schema,
    get_config_section,
    import_config,
    update_config_section,
)
from src.orchestrator.app.schemas.system_config import (
    ConfigImportRequest,
    CorpusConfig,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock async database session."""
    return AsyncMock()


@pytest.fixture
def admin_user():
    """Mock admin user token payload."""
    from datetime import UTC, datetime

    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub="admin",
        user_id="a0000000-0000-0000-0000-000000000001",
        role="admin",
        exp=now + 3600,
        iat=now,
        iss="ai-operations-platform",
        token_type="access",
    )


@pytest.fixture
def corpus_config_data():
    """Sample corpus configuration."""
    return {
        "chunk_size": 512,
        "chunk_overlap": 50,
        "default_embedding_model": "text-embedding-3-small",
        "max_document_size_mb": 50,
        "allowed_file_types": ["pdf", "txt", "docx", "md"],
    }


@pytest.fixture
def full_config_data(corpus_config_data):
    """Sample full system configuration."""
    return {
        "corpus": corpus_config_data,
        "auth": {
            "session_timeout_minutes": 60,
            "refresh_token_ttl_days": 30,
            "password_policy": {
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": False,
            },
        },
        "features": {
            "multi_collection_search": False,
            "export_functionality": True,
            "conversation_cache": True,
            "telemetry_enabled": True,
        },
        "system": {
            "log_level": "INFO",
            "max_workers": 4,
            "request_timeout_seconds": 30,
            "enable_debug_endpoints": False,
        },
    }


# ============================================================================
# Tests: GET /api/v1/admin/config
# ============================================================================


@pytest.mark.asyncio
async def test_get_config_success(mock_db, admin_user, full_config_data):
    """Test successful retrieval of all configuration."""
    # Mock database response
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("auth", full_config_data["auth"]),
        ("corpus", full_config_data["corpus"]),
        ("features", full_config_data["features"]),
        ("system", full_config_data["system"]),
    ]
    mock_db.execute.return_value = mock_result

    # Execute
    result = await get_config(mock_db, admin_user)

    # Verify
    assert result.corpus.chunk_size == 512
    assert result.auth.session_timeout_minutes == 60
    assert result.features.export_functionality is True
    assert result.system.log_level == "INFO"


@pytest.mark.asyncio
async def test_get_config_db_error(mock_db, admin_user):
    """Test get_config handles database errors."""
    mock_db.execute.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await get_config(mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to load configuration" in exc_info.value.detail


# ============================================================================
# Tests: GET /api/v1/admin/config/{section}
# ============================================================================


@pytest.mark.asyncio
async def test_get_config_section_success(mock_db, admin_user, corpus_config_data):
    """Test successful retrieval of configuration section."""
    from datetime import datetime

    # Mock database response
    mock_result = MagicMock()
    updated_at = datetime.now(UTC)
    mock_result.fetchone.return_value = (
        corpus_config_data,
        updated_at,
        "a0000000-0000-0000-0000-000000000001",
    )
    mock_db.execute.return_value = mock_result

    # Execute
    result = await get_config_section("corpus", mock_db, admin_user)

    # Verify
    assert result.section == "corpus"
    assert result.config["chunk_size"] == 512
    assert result.updated_by is not None


@pytest.mark.asyncio
async def test_get_config_section_invalid_section(mock_db, admin_user):
    """Test get_config_section with invalid section name."""
    with pytest.raises(HTTPException) as exc_info:
        await get_config_section("invalid", mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Invalid section" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_config_section_not_found(mock_db, admin_user):
    """Test get_config_section when section doesn't exist."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_config_section("corpus", mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


# ============================================================================
# Tests: PUT /api/v1/admin/config/{section}
# ============================================================================


@pytest.mark.asyncio
async def test_update_config_section_success(mock_db, admin_user, corpus_config_data):
    """Test successful configuration section update."""
    from datetime import datetime

    # Mock database response
    mock_result = MagicMock()
    updated_at = datetime.now(UTC)
    mock_result.fetchone.return_value = (
        corpus_config_data,
        updated_at,
        admin_user.user_id,
    )
    mock_db.execute.return_value = mock_result

    # Execute
    result = await update_config_section("corpus", corpus_config_data, mock_db, admin_user)

    # Verify
    assert result.section == "corpus"
    assert result.config["chunk_size"] == 512
    assert result.restart_required is True  # corpus requires restart
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_config_section_invalid_config(mock_db, admin_user):
    """Test update_config_section with invalid configuration."""
    invalid_config = {"chunk_size": -1}  # Invalid: negative chunk size

    with pytest.raises(HTTPException) as exc_info:
        await update_config_section("corpus", invalid_config, mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid configuration" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_config_section_db_error(mock_db, admin_user, corpus_config_data):
    """Test update_config_section handles database errors."""
    mock_db.execute.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await update_config_section("corpus", corpus_config_data, mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_config_section_not_found(mock_db, admin_user, corpus_config_data):
    """Test update_config_section when section doesn't exist - rollback before 404."""
    # Mock database response with no rows (UPDATE affected nothing)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await update_config_section("corpus", corpus_config_data, mock_db, admin_user)

    # Should raise 404 and rollback (not commit)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail
    mock_db.rollback.assert_awaited_once()
    mock_db.commit.assert_not_awaited()


# ============================================================================
# Tests: GET /api/v1/admin/config/schema/{section}
# ============================================================================


@pytest.mark.asyncio
async def test_get_config_schema_success(admin_user):
    """Test successful retrieval of configuration schema."""
    result = await get_config_schema("corpus", admin_user)

    assert "properties" in result
    assert "chunk_size" in result["properties"]
    assert result["properties"]["chunk_size"]["type"] == "integer"


@pytest.mark.asyncio
async def test_get_config_schema_invalid_section(admin_user):
    """Test get_config_schema with invalid section."""
    with pytest.raises(HTTPException) as exc_info:
        await get_config_schema("invalid", admin_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Tests: POST /api/v1/admin/config/export
# ============================================================================


@pytest.mark.asyncio
async def test_export_config_success(mock_db, admin_user, full_config_data):
    """Test successful configuration export."""
    # Mock get_config
    with patch(
        "src.orchestrator.app.routers.admin_config.get_config",
        new_callable=AsyncMock,
    ) as mock_get_config:
        from src.orchestrator.app.schemas.system_config import SystemConfigFull

        mock_get_config.return_value = SystemConfigFull.model_validate(full_config_data)

        # Execute
        result = await export_config(mock_db, admin_user)

        # Verify
        assert "corpus:" in result.config_yaml
        assert "auth:" in result.config_yaml
        assert result.exported_at is not None


# ============================================================================
# Tests: POST /api/v1/admin/config/import
# ============================================================================


@pytest.mark.asyncio
async def test_import_config_validate_only(mock_db, admin_user, full_config_data):
    """Test configuration import validation without saving."""
    config_yaml = yaml.dump(full_config_data)
    request = ConfigImportRequest(config_yaml=config_yaml, validate_only=True)

    result = await import_config(request, mock_db, admin_user)

    assert result.success is True
    assert len(result.sections_updated) == 0
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_import_config_success(mock_db, admin_user, full_config_data):
    """Test successful configuration import."""
    config_yaml = yaml.dump(full_config_data)
    request = ConfigImportRequest(config_yaml=config_yaml, validate_only=False)

    result = await import_config(request, mock_db, admin_user)

    assert result.success is True
    assert len(result.sections_updated) == 4
    assert "corpus" in result.sections_updated
    assert result.restart_required is True
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_config_invalid_yaml(mock_db, admin_user):
    """Test import_config with invalid YAML."""
    request = ConfigImportRequest(config_yaml="invalid: yaml: content:", validate_only=False)

    with pytest.raises(HTTPException) as exc_info:
        await import_config(request, mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid YAML" in exc_info.value.detail


@pytest.mark.asyncio
async def test_import_config_invalid_schema(mock_db, admin_user):
    """Test import_config with invalid configuration schema."""
    invalid_config = {
        "corpus": {"chunk_size": -1},  # Invalid
        "auth": {},  # Missing required fields
        "features": {},
        "system": {},
    }
    config_yaml = yaml.dump(invalid_config)
    request = ConfigImportRequest(config_yaml=config_yaml, validate_only=False)

    with pytest.raises(HTTPException) as exc_info:
        await import_config(request, mock_db, admin_user)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Tests: Schema Validation
# ============================================================================


def test_corpus_config_validation():
    """Test CorpusConfig validation."""
    # Valid config
    valid = CorpusConfig(
        chunk_size=512,
        chunk_overlap=50,
        default_embedding_model="text-embedding-3-small",
        max_document_size_mb=50,
        allowed_file_types=["pdf", "txt"],
    )
    assert valid.chunk_size == 512

    # Invalid chunk_size (too small)
    with pytest.raises(ValueError):
        CorpusConfig(
            chunk_size=50,  # < 128
            chunk_overlap=50,
            default_embedding_model="test",
            max_document_size_mb=50,
            allowed_file_types=["pdf"],
        )

    # Invalid file types
    with pytest.raises(ValueError):
        CorpusConfig(
            chunk_size=512,
            chunk_overlap=50,
            default_embedding_model="test",
            max_document_size_mb=50,
            allowed_file_types=["invalid_type"],
        )
