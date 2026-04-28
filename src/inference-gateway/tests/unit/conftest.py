"""
Shared test fixtures for unit tests.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Add parent directory to path so 'shared' module can be imported
gateway_root = Path(__file__).parent.parent.parent
src_root = gateway_root.parent
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# Add inference-gateway root so 'app' module can be imported
if str(gateway_root) not in sys.path:
    sys.path.insert(0, str(gateway_root))


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock()
    return session
