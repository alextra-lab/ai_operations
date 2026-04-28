"""
Simplified ProviderManager tests for production readiness.

Focus on critical functionality.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.provider_manager import ProviderManager
from app.utils.errors import ProviderNotFoundError


@pytest.mark.asyncio
async def test_provider_manager_basic_flow():
    """Test basic ProviderManager workflow."""
    manager = ProviderManager()

    # Test initial state
    assert not manager.is_loaded

    # Mock database session and data
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_mappings = Mock()

    sample_data = [
        {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "openai",
            "provider_type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "is_enabled": True,
            "priority": 10,
            "config_json": {},
            "timeout_seconds": 30.0,
        }
    ]

    mock_mappings.all = Mock(return_value=sample_data)
    mock_result.mappings = Mock(return_value=mock_mappings)
    mock_db.execute.return_value = mock_result

    # Test loading
    await manager.load_providers(mock_db)
    assert manager.is_loaded

    # Test get_provider
    config = await manager.get_provider("openai")
    assert config.name == "openai"
    assert config.base_url == "https://api.openai.com/v1"

    # Test cached access
    cached = manager.get_cached_provider("openai")
    assert cached is not None
    assert cached.name == "openai"

    # Test not found
    with pytest.raises(ProviderNotFoundError):
        await manager.get_provider("nonexistent")
