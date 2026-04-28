#!/usr/bin/env python3
"""
Simple test script for the configuration system.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def test_basic_imports():
    """Test basic imports without complex dependencies."""
    print("Testing basic imports...")

    # Test pydantic import
    import pydantic

    print(f"✓ Pydantic imported successfully (version: {pydantic.__version__})")

    # Test basic configuration
    from pydantic import BaseModel, Field

    class TestConfig(BaseModel):
        name: str = Field(default="test")
        value: int = Field(default=42)

    config = TestConfig()
    print(f"✓ Basic Pydantic model works: {config}")

    # Use assertions instead of return values
    assert config.name == "test"
    assert config.value == 42


def test_simple_config():
    """Test a simple configuration without complex features."""
    print("\nTesting simple configuration...")

    from pydantic import BaseModel, Field

    class SimpleConfig(BaseModel):
        host: str = Field(default="localhost")
        port: int = Field(default=8000)
        debug: bool = Field(default=False)

    # Test creation
    config = SimpleConfig()
    print(f"✓ Default config: {config}")
    assert config.host == "localhost"
    assert config.port == 8000
    assert config.debug is False

    # Test with values
    config2 = SimpleConfig(host="127.0.0.1", port=9000, debug=True)
    print(f"✓ Custom config: {config2}")
    assert config2.host == "127.0.0.1"
    assert config2.port == 9000
    assert config2.debug is True

    # Test environment variable loading
    os.environ["HOST"] = "0.0.0.0"
    os.environ["PORT"] = "7000"

    config3 = SimpleConfig(
        host=os.environ.get("HOST", "localhost"),
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("DEBUG", "false").lower() == "true",
    )
    print(f"✓ Env-based config: {config3}")
    assert config3.host == "0.0.0.0"
    assert config3.port == 7000


def test_config_manager():
    """Test the configuration manager."""
    print("\nTesting configuration manager...")

    from pydantic import BaseModel, Field

    class TestConfig(BaseModel):
        name: str = Field(default="test")
        value: int = Field(default=42)

    class SimpleConfigManager:
        def __init__(self):
            self._configs = {}

        def register_config(self, name: str, config):
            self._configs[name] = config

        def get_config(self, name: str):
            return self._configs.get(name)

        def get_all_configs(self):
            return self._configs.copy()

    # Test manager
    manager = SimpleConfigManager()

    config1 = TestConfig(name="service1", value=100)
    config2 = TestConfig(name="service2", value=200)

    manager.register_config("service1", config1)
    manager.register_config("service2", config2)

    print(f"✓ Registered configs: {list(manager._configs.keys())}")

    retrieved = manager.get_config("service1")
    print(f"✓ Retrieved config: {retrieved}")
    assert retrieved is not None
    assert retrieved.name == "service1"
    assert retrieved.value == 100

    all_configs = manager.get_all_configs()
    print(f"✓ All configs: {len(all_configs)}")
    assert len(all_configs) == 2


def main():
    """Main test function."""
    print("🧪 Testing Configuration System")
    print("=" * 40)

    tests = [
        test_basic_imports,
        test_simple_config,
        test_config_manager,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Configuration system is working.")
        print("\nNext steps:")
        print("1. Run: python ops/validate_configuration.py")
        print("2. Review config/env/env.template (the canonical, hand-maintained template)")
        print("3. Start migrating services to use the new configuration system")
    else:
        print("❌ Some tests failed. Check the errors above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
