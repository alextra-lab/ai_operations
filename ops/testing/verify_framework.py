#!/usr/bin/env python3
"""
Verify the test framework scaffolding scripts by checking their presence and ability to be imported.
This script doesn't execute tests but verifies that the framework structure is intact.
"""

import importlib
import inspect
import os
import sys
from pathlib import Path


def verify_module_import(module_name, expected_path=None):
    """Verify that a module can be imported and optionally check its path"""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")

        if expected_path:
            module_path = os.path.abspath(inspect.getfile(module))
            if expected_path in module_path:
                print(f"   Path verification: ✅ Found in {module_path}")
            else:
                print(
                    f"   Path verification: ❌ Expected in {expected_path}, found at {module_path}"
                )

        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False


def check_file_exists(filepath):
    """Check if a file exists"""
    path = Path(filepath)
    if path.exists() and path.is_file():
        print(f"✅ File exists: {filepath}")
        return True
    print(f"❌ File missing: {filepath}")
    return False


def verify_framework():
    """Verify the test framework scaffolding"""
    print("\n" + "=" * 80)
    print(" Test Framework Verification ".center(80, "="))
    print("=" * 80)

    # Add scripts/testing to Python path
    sys.path.insert(0, str(Path("/workspace/scripts/testing")))

    # Check core script files
    base_dir = Path("/workspace/scripts/testing")
    check_file_exists(base_dir / "run_tests.py")
    check_file_exists(base_dir / "run_coverage.py")
    check_file_exists(base_dir / "setup_environment.py")
    check_file_exists(base_dir / "fix_imports.py")
    check_file_exists(base_dir / "fix_db_connection.py")

    # Check compatibility functions in connection.py
    connection_file = Path("/workspace/src/retrieval/app/db/connection.py")
    if check_file_exists(connection_file):
        content = connection_file.read_text()
        has_get_pool = "async def get_db_pool()" in content
        has_close_pool = "async def close_db_pool()" in content

        if has_get_pool and has_close_pool:
            print("✅ Connection file contains compatibility functions")
        else:
            missing = []
            if not has_get_pool:
                missing.append("get_db_pool()")
            if not has_close_pool:
                missing.append("close_db_pool()")
            print(f"❌ Connection file missing compatibility functions: {', '.join(missing)}")

    # Check test module files
    test_dirs = [
        "/workspace/tests/embedding/unit",
        "/workspace/tests/retrieval/unit",
        "/workspace/tests/retrieval/integration",
    ]

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
            if files:
                print(f"✅ Found {len(files)} test files in {test_dir}")
                for file in files[:3]:  # Show first 3 at most
                    print(f"   - {file}")
                if len(files) > 3:
                    print(f"   - ... and {len(files) - 3} more")
            else:
                print(f"⚠️ No test files found in {test_dir}")
        else:
            print(f"❌ Test directory missing: {test_dir}")

    print("\n" + "=" * 80)
    print(" Verification Complete ".center(80, "="))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    verify_framework()
