"""
Root pytest configuration.

Adds service directories to sys.path so tests can import modules using
relative paths like 'from app.database import ...' when running from project root.

This is necessary because some directories (e.g., inference-gateway) have hyphens
in their names and can't be imported as Python packages directly.
"""

import sys
from pathlib import Path

# Project root
project_root = Path(__file__).parent

# Add src directory for shared module access
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Add individual service directories so 'app' module can be imported
# This is needed for services with hyphens in directory names
service_dirs = [
    src_dir / "inference-gateway",
    src_dir / "orchestrator",
    src_dir / "corpus_svc",
    src_dir / "embedding",
    src_dir / "llm_guard_svc",
]

for service_dir in service_dirs:
    if service_dir.exists() and str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
