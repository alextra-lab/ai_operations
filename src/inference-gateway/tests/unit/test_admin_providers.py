"""
Unit tests for Provider Management Admin API.

Tests CRUD operations for gateway providers.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from shared.providers import ProviderConfig, ProviderConfigUpdate  # type: ignore[import-untyped]

import app.routers.admin as admin_module

create_provider = admin_module.create_provider  # type: ignore[attr-defined]
delete_provider = admin_module.delete_provider  # type: ignore[attr-defined]
get_provider = admin_module.get_provider  # type: ignore[attr-defined]
list_providers = admin_module.list_providers  # type: ignore[attr-defined]
test_provider = admin_module.test_provider  # type: ignore[attr-defined]
update_provider = admin_module.update_provider  # type: ignore[attr-defined]


@pytest.fixture
def mock_token():
    """Mock JWT token payload."""
    token = MagicMock()
    token.sub = str(uuid4())
    token.user_id = str(uuid4())
    token.role = "admin"
    return token


@pytest.fixture
def sample_provider():
    """Sample provider configuration."""
    return {
        "id": uuid4(),
        "name": "OpenAI Production",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "is_enabled": True,
        "status": "active",
        "priority": 100,
        "config_json": {},
        "health_check_url": None,
        "last_health_check": None,
        "last_health_status": None,
        "error_count": 0,
        "success_count": 10,
        "circuit_state": "CLOSED",
        "created_at": "2025-11-03T10:00:00",
        "updated_at": "2025-11-03T10:00:00",
    }


@pytest.mark.asyncio
class TestListProviders:
    """Test list_providers endpoint."""

    async def test_list_providers_success(self, mock_token, sample_provider):
        """Test successful provider listing."""
        with patch("app.routers.admin.get_db") as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock count query
            mock_count = MagicMock()
            mock_count.scalar.return_value = 1

            # Mock select query
            mock_select = MagicMock()
            mock_select.fetchall.return_value = [
                (
                    sample_provider["id"],
                    sample_provider["name"],
                    sample_provider["provider_type"],
                    sample_provider["base_url"],
                    sample_provider["is_enabled"],
                    sample_provider["status"],
                    sample_provider["priority"],
                    sample_provider["config_json"],
                    sample_provider["health_check_url"],
                    None,  # last_health_check
                    None,  # last_health_status
                    sample_provider["error_count"],
                    sample_provider["success_count"],
                    sample_provider["circuit_state"],
                    None,  # created_at
                    None,  # updated_at
                )
            ]

            mock_session.execute = AsyncMock(side_effect=[mock_count, mock_select])

            # Call function
            result = await list_providers(limit=20, offset=0, enabled_only=False, token=mock_token)

            # Assertions
            assert result.total == 1
            assert len(result.items) == 1
            assert result.items[0].name == "OpenAI Production"
            assert result.items[0].provider_type == "openai"

    async def test_list_providers_enabled_only(self, mock_token):
        """Test listing enabled providers only."""
        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            mock_count = MagicMock()
            mock_count.scalar.return_value = 0
            mock_select = MagicMock()
            mock_select.fetchall.return_value = []

            mock_session.execute = AsyncMock(side_effect=[mock_count, mock_select])

            result = await list_providers(limit=20, offset=0, enabled_only=True, token=mock_token)

            assert result.total == 0
            assert len(result.items) == 0


@pytest.mark.asyncio
class TestGetProvider:
    """Test get_provider endpoint."""

    async def test_get_provider_success(self, mock_token, sample_provider):
        """Test successful provider retrieval."""
        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.fetchone.return_value = (
                sample_provider["id"],
                sample_provider["name"],
                sample_provider["provider_type"],
                sample_provider["base_url"],
                sample_provider["is_enabled"],
                sample_provider["status"],
                sample_provider["priority"],
                sample_provider["config_json"],
                sample_provider["health_check_url"],
                None,
                None,
                sample_provider["error_count"],
                sample_provider["success_count"],
                sample_provider["circuit_state"],
                None,
                None,
            )

            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await get_provider(provider_id=sample_provider["id"], token=mock_token)

            assert result.name == "OpenAI Production"
            assert result.provider_type == "openai"

    async def test_get_provider_not_found(self, mock_token):
        """Test provider not found."""
        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            with pytest.raises(Exception):  # HTTPException
                await get_provider(provider_id=uuid4(), token=mock_token)


@pytest.mark.asyncio
class TestCreateProvider:
    """Test create_provider endpoint."""

    async def test_create_provider_success(self, mock_token):
        """Test successful provider creation."""
        config = ProviderConfig(
            name="Mistral Production",
            provider_type="mistral",
            base_url="https://api.mistral.ai",
            is_enabled=True,
            status="testing",
            priority=100,
        )

        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock check for existing provider
            mock_check = MagicMock()
            mock_check.fetchone.return_value = None

            # Mock insert result
            new_id = uuid4()
            mock_insert = MagicMock()
            mock_insert.fetchone.return_value = (new_id, None, None)

            mock_session.execute = AsyncMock(side_effect=[mock_check, mock_insert])
            mock_session.commit = AsyncMock()

            result = await create_provider(config=config, token=mock_token)

            assert result.id == new_id
            assert result.name == "Mistral Production"
            assert result.api_key is None  # Should be cleared

            # Ensure JSON payload is serialized before insert
            # The second call (index 1) is the INSERT query
            insert_call = mock_session.execute.await_args_list[1]
            # execute() is called with (query, params_dict) - params_dict is the second positional arg
            call_args = insert_call[0] if isinstance(insert_call, tuple) else insert_call.args
            call_kwargs = insert_call.kwargs if hasattr(insert_call, "kwargs") else {}
            # params_dict is the second positional argument
            params_dict = call_args[1] if len(call_args) > 1 else call_kwargs
            assert "config_json" in params_dict
            assert params_dict["config_json"] == json.dumps({})

    async def test_create_provider_duplicate_name(self, mock_token):
        """Test creating provider with duplicate name."""
        config = ProviderConfig(
            name="OpenAI Production",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            is_enabled=True,
            status="testing",
            priority=100,
        )

        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock existing provider found
            mock_check = MagicMock()
            mock_check.fetchone.return_value = (uuid4(),)
            mock_session.execute.return_value = mock_check

            with pytest.raises(Exception):  # HTTPException 409
                await create_provider(config=config, token=mock_token)


@pytest.mark.asyncio
class TestUpdateProvider:
    """Test update_provider endpoint."""

    async def test_update_provider_success(self, mock_token, sample_provider):
        """Test successful provider update."""
        config = ProviderConfigUpdate(
            is_enabled=False,  # Disable
            status="disabled",
        )

        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock update result
            mock_update = MagicMock()
            mock_update.fetchone.return_value = (None,)

            # Mock get_provider result (called after update)
            mock_get_result = MagicMock()
            mock_get_result.fetchone.return_value = (
                sample_provider["id"],
                sample_provider["name"],
                sample_provider["provider_type"],
                sample_provider["base_url"],
                False,  # Updated is_enabled
                "disabled",  # Updated status
                sample_provider["priority"],
                sample_provider["config_json"],
                sample_provider["health_check_url"],
                None,
                None,
                sample_provider["error_count"],
                sample_provider["success_count"],
                sample_provider["circuit_state"],
                None,
                None,
            )

            # execute() is called twice: once for update, once for get_provider
            call_count = 0

            async def execute_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_update  # Update query
                else:
                    return mock_get_result  # Get query

            mock_session.execute = AsyncMock(side_effect=execute_side_effect)
            mock_session.commit = AsyncMock()

            result = await update_provider(
                provider_id=sample_provider["id"],
                config=config,
                token=mock_token,
            )

            assert result.name == "OpenAI Production"
            assert result.is_enabled is False

            # Ensure no config_json is sent when not provided
            # Check the first call (update query)
            update_call = mock_session.execute.await_args_list[0]
            call_args = update_call[0] if isinstance(update_call, tuple) else update_call.args
            call_kwargs = update_call.kwargs if hasattr(update_call, "kwargs") else {}
            params_dict = call_args[1] if len(call_args) > 1 else call_kwargs
            assert "config_json" not in params_dict

    async def test_update_provider_with_config_json(self, mock_token, sample_provider):
        """Test provider update serializes config_json."""

        config = ProviderConfigUpdate(
            priority=50,
            config_json={"timeout": 30},
        )

        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock update result
            mock_update = MagicMock()
            mock_update.fetchone.return_value = (None,)

            # Mock get_provider result (called after update)
            mock_get_result = MagicMock()
            mock_get_result.fetchone.return_value = (
                sample_provider["id"],
                sample_provider["name"],
                sample_provider["provider_type"],
                sample_provider["base_url"],
                sample_provider["is_enabled"],
                sample_provider["status"],
                50,  # Updated priority
                {"timeout": 30},  # Updated config_json
                sample_provider["health_check_url"],
                None,
                None,
                sample_provider["error_count"],
                sample_provider["success_count"],
                sample_provider["circuit_state"],
                None,
                None,
            )

            # execute() is called twice: once for update, once for get_provider
            call_count = 0

            async def execute_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_update  # Update query
                else:
                    return mock_get_result  # Get query

            mock_session.execute = AsyncMock(side_effect=execute_side_effect)
            mock_session.commit = AsyncMock()

            await update_provider(
                provider_id=sample_provider["id"],
                config=config,
                token=mock_token,
            )

            # Check the first call (update query) for config_json
            update_call = mock_session.execute.await_args_list[0]
            call_args = update_call[0] if isinstance(update_call, tuple) else update_call.args
            call_kwargs = update_call.kwargs if hasattr(update_call, "kwargs") else {}
            params_dict = call_args[1] if len(call_args) > 1 else call_kwargs
            assert json.loads(params_dict["config_json"]) == {"timeout": 30}


@pytest.mark.asyncio
class TestDeleteProvider:
    """Test delete_provider endpoint."""

    async def test_delete_provider_success(self, mock_token, sample_provider):
        """Test successful provider deletion."""
        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            mock_delete = MagicMock()
            mock_delete.fetchone.return_value = (sample_provider["id"],)
            mock_session.execute = AsyncMock(return_value=mock_delete)
            mock_session.commit = AsyncMock()

            await delete_provider(provider_id=sample_provider["id"], token=mock_token)

            # Verify delete query was executed
            assert mock_session.execute.await_count == 1
            assert mock_session.commit.await_count == 1

    async def test_delete_provider_not_found(self, mock_token):
        """Test deleting non-existent provider."""
        provider_id = uuid4()
        with patch("app.routers.admin.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            mock_delete = MagicMock()
            mock_delete.fetchone.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_delete)

            with pytest.raises(Exception):  # HTTPException 404
                await delete_provider(provider_id=provider_id, token=mock_token)


@pytest.mark.asyncio
class TestTestProvider:
    """Test test_provider endpoint."""

    async def test_test_provider_success(self, mock_token, sample_provider):
        """Test successful provider connectivity test."""
        with patch("app.routers.admin.get_provider") as mock_get:
            mock_get.return_value = ProviderConfig(**sample_provider)

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=MagicMock(status_code=200)
                )

                with patch("app.routers.admin.get_db") as mock_db:
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    mock_session.execute = AsyncMock()
                    mock_session.commit = AsyncMock()

                    result = await test_provider(
                        provider_id=sample_provider["id"], token=mock_token
                    )

                    assert result["success"] is True
                    assert result["status_code"] == 200
                    assert "latency_ms" in result
