"""
Shared fixtures for database unit tests.

Adds inference-gateway to sys.path so 'app' module can be imported when
running tests from the project root.
"""

import sys
from pathlib import Path

# Add inference-gateway root so 'app' module can be imported
gateway_root = Path(__file__).parent.parent.parent.parent
if str(gateway_root) not in sys.path:
    sys.path.insert(0, str(gateway_root))
