#!/usr/bin/env python3
"""
Load test environment variables from env.test file.

This script loads environment variables from the test environment file
and makes them available to the current process.
"""

import os
import sys
from pathlib import Path


def load_test_env():
    """Load test environment variables from env.test file for unit tests."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    # Try env.test.local first, fall back to env.test
    env_file = project_root / "config" / "env" / "env.test.local"
    if not env_file.exists():
        env_file = project_root / "config" / "env" / "env.test"

    if not env_file.exists():
        print(f"❌ Test environment file not found: {env_file}")
        print("Please ensure config/env/env.test exists")
        sys.exit(1)

    print(f"📋 Loading test environment from: {env_file}")

    # Load environment variables from the file
    with open(env_file) as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]

                # Set environment variable
                os.environ[key] = value
                print(f"  ✅ {key}={value[:20]}{'...' if len(value) > 20 else ''}")

    print("🎉 Test environment loaded successfully!")
    return True


if __name__ == "__main__":
    load_test_env()
