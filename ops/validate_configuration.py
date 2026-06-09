#!/usr/bin/env python3
"""
Configuration validation script for the AI Operations Platform (AIOP) stack.

This script validates that all services have consistent configuration
and that environment variables are properly set.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from shared.config import config_manager
    from shared.config.loader import load_all_configs, validate_all_configs
    from shared.config.version import CONFIG_SCHEMA_VERSION
except ImportError as e:
    print(f"Error importing configuration modules: {e}")
    print("Install the host ops dependencies in a virtualenv first:")
    print("    python3.12 -m venv .venv && source .venv/bin/activate")
    print("    pip install -r requirements-ops.txt")
    print("Then run this script from the project root directory.")
    sys.exit(1)


def check_environment_variables() -> dict[str, list[str]]:
    """Check for required and optional environment variables."""
    results: dict[str, list[str]] = {
        "missing_required": [],
        "missing_optional": [],
        "insecure_values": [],
        "found": [],
    }

    # Required environment variables
    required_vars = [
        "JWT_SECRET",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]

    # Optional but important environment variables
    optional_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "QDRANT_HOST",
        "QDRANT_PORT",
        "OPENAI_API_KEY",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ]

    # Check required variables
    for var in required_vars:
        if var not in os.environ:
            results["missing_required"].append(var)
        else:
            value = os.environ[var]
            results["found"].append(f"{var}={value}")

            # Check for insecure values
            if var == "JWT_SECRET" and value in ["myTopsecretkey", "mysecretkey"]:
                results["insecure_values"].append(f"{var}={value}")

    # Check optional variables
    for var in optional_vars:
        if var not in os.environ:
            results["missing_optional"].append(var)
        else:
            results["found"].append(f"{var}={os.environ[var]}")

    return results


def _read_version_from_file(path: Path) -> str | None:
    """Read CONFIG_SCHEMA_VERSION value from an env file."""
    if not path.exists():
        return None

    try:
        with open(path) as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("CONFIG_SCHEMA_VERSION"):
                    _, _, value = line.partition("=")
                    return value.strip().strip('"').strip("'")
                break
    except OSError:
        return None
    return None


def check_config_version() -> dict[str, Any]:
    """Verify configuration schema version across templates and environment."""
    expected_version = CONFIG_SCHEMA_VERSION
    template_version = _read_version_from_file(project_root / "config" / "env" / "env.template")
    test_template_version = _read_version_from_file(
        project_root / "config" / "env" / "env.test.template"
    )
    local_env_version = _read_version_from_file(project_root / "config" / "env" / ".env")
    if local_env_version is None:
        local_env_version = _read_version_from_file(project_root / ".env")
    local_test_version = _read_version_from_file(project_root / "config" / "env" / ".env.test")
    if local_test_version is None:
        local_test_version = _read_version_from_file(project_root / ".env.test")
    runtime_version = os.environ.get("CONFIG_SCHEMA_VERSION")

    return {
        "expected": expected_version,
        "template": template_version,
        "test_template": test_template_version,
        "local_env": local_env_version,
        "local_test": local_test_version,
        "runtime": runtime_version,
    }


def check_docker_compose_consistency() -> dict[str, list[str]]:
    """Check consistency between docker-compose.yml and configuration."""
    results: dict[str, list[str]] = {"inconsistencies": [], "warnings": []}

    docker_compose_path = project_root / "deploy" / "docker-compose.yml"
    if not docker_compose_path.exists():
        results["warnings"].append("docker-compose.yml not found")
        return results

    try:
        with open(docker_compose_path) as f:
            content = f.read()

        # Check for hardcoded values that should be environment variables
        hardcoded_issues = [
            ("JWT_SECRET", "myTopsecretkey"),
            ("POSTGRES_USER", "user"),
            ("POSTGRES_PASSWORD", "password"),
            ("POSTGRES_DB", "aio"),
        ]

        for var, value in hardcoded_issues:
            if f"{var}={value}" in content:
                results["inconsistencies"].append(
                    f"Hardcoded {var}={value} in docker-compose.yml should use environment variable"
                )

        # Check for missing environment variable references
        if "POSTGRES_HOST" not in content:
            results["warnings"].append("POSTGRES_HOST not referenced in docker-compose.yml")

    except Exception as e:
        results["warnings"].append(f"Error reading docker-compose.yml: {e}")

    return results


def check_service_configurations() -> dict[str, Any]:
    """Check service-specific configuration files."""
    results: dict[str, Any] = {"embedding": {}, "retrieval": {}, "backend": {}, "llm_guard": {}}

    # Check embedding service config
    embedding_config_path = src_path / "embedding" / "app" / "config" / "models.yaml"
    if embedding_config_path.exists():
        try:
            import yaml

            with open(embedding_config_path) as f:
                config = yaml.safe_load(f)
            results["embedding"]["config_file"] = "Found"
            results["embedding"]["providers"] = len(config.get("providers", []))
        except Exception as e:
            results["embedding"]["config_file"] = f"Error: {e}"
    else:
        results["embedding"]["config_file"] = "Not found"

    # Check retrieval service config
    retrieval_main_path = src_path / "retrieval" / "app" / "main.py"
    if retrieval_main_path.exists():
        try:
            with open(retrieval_main_path) as f:
                content = f.read()
            # Count environment variable usage
            env_vars = [line.strip() for line in content.split("\n") if "os.environ.get(" in line]
            results["retrieval"]["env_vars_used"] = len(env_vars)
            results["retrieval"]["config_file"] = "Found"
        except Exception as e:
            results["retrieval"]["config_file"] = f"Error: {e}"
    else:
        results["retrieval"]["config_file"] = "Not found"

    return results


def main():
    """Main validation function."""
    print("🔍 AI Operations Platform (AIOP) Configuration Validation")
    print("=" * 50)

    # Check environment variables
    print("\n📋 Environment Variables Check:")
    env_results = check_environment_variables()

    if env_results["missing_required"]:
        print("  ❌ Missing required environment variables:")
        for var in env_results["missing_required"]:
            print(f"    - {var}")
    else:
        print("  ✅ All required environment variables are set")

    if env_results["missing_optional"]:
        print("  ⚠️  Missing optional environment variables:")
        for var in env_results["missing_optional"]:
            print(f"    - {var}")

    if env_results["insecure_values"]:
        print("  ⚠️  Insecure environment variable values:")
        for var in env_results["insecure_values"]:
            print(f"    - {var}")

    if env_results["found"]:
        print(f"  📝 Found {len(env_results['found'])} environment variables")

    # Config schema version check
    print("\n🧾 Configuration Schema Version:")
    version_info = check_config_version()
    expected_version = version_info["expected"]
    mismatches = []

    def _status(label: str, value: str | None) -> None:
        if value == expected_version:
            print(f"  ✅ {label}: {value}")
        elif value is None:
            print(f"  ⚠️  {label}: not found")
            mismatches.append(label)
        else:
            print(f"  ❌ {label}: {value} (expected {expected_version})")
            mismatches.append(label)

    _status("env.template", version_info["template"])
    _status("env.test.template", version_info["test_template"])
    _status(".env", version_info["local_env"])
    _status(".env.test", version_info["local_test"])
    _status("runtime environment", version_info["runtime"])

    # Check Docker Compose consistency
    print("\n🐳 Docker Compose Consistency Check:")
    docker_results = check_docker_compose_consistency()

    if docker_results["inconsistencies"]:
        print("  ❌ Configuration inconsistencies found:")
        for issue in docker_results["inconsistencies"]:
            print(f"    - {issue}")
    else:
        print("  ✅ Docker Compose configuration is consistent")

    if docker_results["warnings"]:
        print("  ⚠️  Warnings:")
        for warning in docker_results["warnings"]:
            print(f"    - {warning}")

    # Check service configurations
    print("\n⚙️  Service Configuration Check:")
    service_results = check_service_configurations()

    for service, config in service_results.items():
        print(f"  {service.title()} Service:")
        for key, value in config.items():
            print(f"    - {key}: {value}")

    # Load and validate centralized configurations
    print("\n🔧 Centralized Configuration Validation:")
    try:
        load_all_configs()
        if validate_all_configs():
            print("  ✅ All centralized configurations are valid")
        else:
            print("  ❌ Some centralized configurations are invalid")

        # Show loaded configurations
        all_configs = config_manager.get_all_configs()
        print(f"  📊 Loaded {len(all_configs)} configuration types:")
        for config_name in all_configs:
            print(f"    - {config_name}")

    except Exception as e:
        print(f"  ❌ Error loading centralized configurations: {e}")

    # Summary
    print("\n📊 Validation Summary:")
    total_issues = (
        len(env_results["missing_required"])
        + len(env_results["insecure_values"])
        + len(docker_results["inconsistencies"])
        + len(mismatches)
    )

    if total_issues == 0:
        print("  🎉 Configuration is consistent and secure!")
    else:
        print(f"  ⚠️  Found {total_issues} configuration issues that should be addressed")

    print("\n💡 Recommendations:")
    if env_results["missing_required"]:
        print("  - Set all required environment variables")
    if env_results["insecure_values"]:
        print("  - Use secure values for sensitive environment variables")
    if docker_results["inconsistencies"]:
        print("  - Update docker-compose.yml to use environment variables consistently")
    if mismatches:
        print("  - Refresh configuration files from templates to match the schema version")
    print("  - Use the centralized configuration system for new services")
    print("  - Run this validation script regularly to maintain consistency")


if __name__ == "__main__":
    main()
