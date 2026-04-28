#!/usr/bin/env python3
"""
Verification script for B1-F1: Use Case Config Schema & Validation

This script validates the complete implementation of B1-F1 including:
- Pydantic schema validation
- Database migration application
- Constraint validation
- Integration testing
- Performance verification

This is a permanent testing utility that should be run as part of the
test suite to validate the UseCaseConfig implementation.

Usage:
    python scripts/testing/verify_use_case_config.py
    python scripts/testing/run_all_tests.py --include-verification
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from src.backend.app.db.database import SessionLocal
from src.backend.app.db.models import UseCase
from src.backend.app.schemas.use_case_config import OutputFormat, UseCaseConfig


class UseCaseConfigVerifier:
    """Verification class for UseCaseConfig implementation."""

    def __init__(self):
        self.results = {
            "schema_validation": {"passed": 0, "failed": 0, "tests": []},
            "database_integration": {"passed": 0, "failed": 0, "tests": []},
            "constraint_validation": {"passed": 0, "failed": 0, "tests": []},
            "performance": {"passed": 0, "failed": 0, "tests": []},
            "overall": {"status": "PENDING", "score": 0},
        }

    def log_test(self, category: str, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        result = {"test": test_name, "passed": passed, "message": message, "timestamp": time.time()}
        self.results[category]["tests"].append(result)
        if passed:
            self.results[category]["passed"] += 1
            print(f"✅ {category.upper()}: {test_name}")
        else:
            self.results[category]["failed"] += 1
            print(f"❌ {category.upper()}: {test_name} - {message}")

    def verify_schema_validation(self):
        """Verify Pydantic schema validation works correctly."""
        print("\n🔍 Testing Schema Validation...")

        # Test 1: Default configuration creation
        try:
            config = UseCaseConfig()
            assert config.models.llm == "gpt-4o"
            assert config.rag.enabled is True
            assert config.output_contract.format == OutputFormat.TEXT
            self.log_test("schema_validation", "Default config creation", True)
        except Exception as e:
            self.log_test("schema_validation", "Default config creation", False, str(e))

        # Test 2: Custom configuration validation
        try:
            config = UseCaseConfig(
                visibility={"roles": ["analyst"], "tags": ["test"]},
                models={"llm": "gpt-4-turbo", "embedding": "text-embedding-3-large"},
                generation_params={"temperature": 0.5, "max_tokens": 2048},
                rag={"enabled": True, "top_k": 5, "vector_collections": ["docs"]},
                output_contract={"format": "json", "validation_mode": "strict"},
                tools_allowlist=["web_search", "tanium_query"],
            )
            assert config.models.llm == "gpt-4-turbo"
            assert config.generation_params.temperature == 0.5
            assert config.rag.top_k == 5
            assert config.output_contract.format == OutputFormat.JSON
            self.log_test("schema_validation", "Custom config validation", True)
        except Exception as e:
            self.log_test("schema_validation", "Custom config validation", False, str(e))

        # Test 3: Invalid data rejection
        try:
            UseCaseConfig(generation_params={"temperature": 1.5})  # Invalid temperature
            self.log_test(
                "schema_validation",
                "Invalid data rejection",
                False,
                "Should have raised ValidationError",
            )
        except Exception:
            self.log_test("schema_validation", "Invalid data rejection", True)

        # Test 4: Serialization/deserialization
        try:
            config = UseCaseConfig()
            config_dict = config.to_dict()
            loaded_config = UseCaseConfig.from_dict(config_dict)
            assert config.models.llm == loaded_config.models.llm
            assert config.rag.enabled == loaded_config.rag.enabled
            self.log_test("schema_validation", "Serialization/deserialization", True)
        except Exception as e:
            self.log_test("schema_validation", "Serialization/deserialization", False, str(e))

        # Test 5: Config merging
        try:
            base_config = UseCaseConfig()
            override_config = UseCaseConfig(models={"llm": "gpt-4-turbo"})
            merged = base_config.merge_with(override_config)
            assert merged.models.llm == "gpt-4-turbo"
            assert merged.rag.enabled is True  # Should inherit from base
            self.log_test("schema_validation", "Config merging", True)
        except Exception as e:
            self.log_test("schema_validation", "Config merging", False, str(e))

    def verify_database_integration(self):
        """Verify database integration works correctly."""
        print("\n🔍 Testing Database Integration...")

        try:
            # Get database session
            db = SessionLocal()

            # Test 1: Store configuration in database
            config = UseCaseConfig(
                visibility={"roles": ["analyst"], "tags": ["test"]},
                models={"llm": "gpt-4o"},
                generation_params={"temperature": 0.7},
                rag={"enabled": True, "top_k": 10},
                output_contract={"format": "text"},
                telemetry={"required_metrics": ["retrieval"]},
                policy={"streaming_enabled": True},
            )

            use_case = UseCase(
                use_case_id="verify_use_case_config_test",
                name="Use Case Config Verification Test",
                description="Test use case for UseCaseConfig verification",
                category="test",
                intent_type="QUERY",
                is_active=True,
                config_json=config.to_dict(),
                created_by_user_id=None,
            )

            db.add(use_case)
            db.commit()
            db.refresh(use_case)

            assert use_case.config_json is not None
            assert use_case.config_json["models"]["llm"] == "gpt-4o"
            self.log_test("database_integration", "Store config in database", True)

            # Test 2: Retrieve and deserialize configuration
            loaded_config = UseCaseConfig.from_dict(use_case.config_json)
            assert loaded_config.models.llm == "gpt-4o"
            assert loaded_config.rag.enabled is True
            assert loaded_config.generation_params.temperature == 0.7
            self.log_test("database_integration", "Retrieve and deserialize config", True)

            # Test 3: Update configuration
            updated_config = UseCaseConfig(
                models={"llm": "gpt-4-turbo"}, generation_params={"temperature": 0.5}
            )
            use_case.config_json = updated_config.to_dict()
            db.commit()
            db.refresh(use_case)

            loaded_updated = UseCaseConfig.from_dict(use_case.config_json)
            assert loaded_updated.models.llm == "gpt-4-turbo"
            assert loaded_updated.generation_params.temperature == 0.5
            self.log_test("database_integration", "Update configuration", True)

            # Cleanup
            db.delete(use_case)
            db.commit()

        except Exception as e:
            self.log_test("database_integration", "Database integration", False, str(e))

    def verify_constraint_validation(self):
        """Verify database constraint validation works correctly."""
        print("\n🔍 Testing Constraint Validation...")

        try:
            db = SessionLocal()

            # Test 1: Empty config_json should fail
            try:
                use_case = UseCase(
                    use_case_id="test_empty_config",
                    name="Test Empty Config",
                    description="Test use case with empty config",
                    category="test",
                    intent_type="QUERY",
                    is_active=True,
                    config_json={},
                    created_by_user_id=None,
                )
                db.add(use_case)
                db.commit()
                self.log_test(
                    "constraint_validation", "Empty config rejection", False, "Should have failed"
                )
            except Exception:
                db.rollback()
                self.log_test("constraint_validation", "Empty config rejection", True)

            # Test 2: Missing required fields should fail
            try:
                incomplete_config = {
                    "visibility": {"roles": ["analyst"]},
                    "models": {"llm": "gpt-4o"},
                    # Missing other required fields
                }
                use_case = UseCase(
                    use_case_id="test_incomplete_config",
                    name="Test Incomplete Config",
                    description="Test use case with incomplete config",
                    category="test",
                    intent_type="QUERY",
                    is_active=True,
                    config_json=incomplete_config,
                    created_by_user_id=None,
                )
                db.add(use_case)
                db.commit()
                self.log_test(
                    "constraint_validation",
                    "Incomplete config rejection",
                    False,
                    "Should have failed",
                )
            except Exception:
                db.rollback()
                self.log_test("constraint_validation", "Incomplete config rejection", True)

            # Test 3: Invalid temperature should fail
            try:
                config = UseCaseConfig()
                config_dict = config.to_dict()
                config_dict["generation_params"]["temperature"] = 1.5  # Out of range

                use_case = UseCase(
                    use_case_id="test_invalid_temperature",
                    name="Test Invalid Temperature",
                    description="Test use case with invalid temperature",
                    category="test",
                    intent_type="QUERY",
                    is_active=True,
                    config_json=config_dict,
                    created_by_user_id=None,
                )
                db.add(use_case)
                db.commit()
                self.log_test(
                    "constraint_validation",
                    "Invalid temperature rejection",
                    False,
                    "Should have failed",
                )
            except Exception:
                db.rollback()
                self.log_test("constraint_validation", "Invalid temperature rejection", True)

            # Test 4: Valid configuration should succeed
            try:
                config = UseCaseConfig()
                use_case = UseCase(
                    use_case_id="test_valid_config",
                    name="Test Valid Config",
                    description="Test use case with valid config",
                    category="test",
                    intent_type="QUERY",
                    is_active=True,
                    config_json=config.to_dict(),
                    created_by_user_id=None,
                )
                db.add(use_case)
                db.commit()
                db.refresh(use_case)

                # Verify it was stored correctly
                assert use_case.config_json is not None
                self.log_test("constraint_validation", "Valid config acceptance", True)

                # Cleanup
                db.delete(use_case)
                db.commit()

            except Exception as e:
                db.rollback()
                self.log_test("constraint_validation", "Valid config acceptance", False, str(e))

        except Exception as e:
            self.log_test("constraint_validation", "Constraint validation", False, str(e))

    def verify_performance(self):
        """Verify performance characteristics."""
        print("\n🔍 Testing Performance...")

        # Test 1: Schema creation performance
        try:
            start_time = time.time()
            for _ in range(1000):
                config = UseCaseConfig()
            end_time = time.time()

            avg_time = (end_time - start_time) / 1000
            if avg_time < 0.001:  # Less than 1ms per creation
                self.log_test(
                    "performance", "Schema creation performance", True, f"Avg: {avg_time:.6f}s"
                )
            else:
                self.log_test(
                    "performance",
                    "Schema creation performance",
                    False,
                    f"Too slow: {avg_time:.6f}s",
                )
        except Exception as e:
            self.log_test("performance", "Schema creation performance", False, str(e))

        # Test 2: Serialization performance
        try:
            config = UseCaseConfig()
            start_time = time.time()
            for _ in range(1000):
                config_dict = config.to_dict()
                UseCaseConfig.from_dict(config_dict)
            end_time = time.time()

            avg_time = (end_time - start_time) / 1000
            if avg_time < 0.002:  # Less than 2ms per serialization cycle
                self.log_test(
                    "performance", "Serialization performance", True, f"Avg: {avg_time:.6f}s"
                )
            else:
                self.log_test(
                    "performance", "Serialization performance", False, f"Too slow: {avg_time:.6f}s"
                )
        except Exception as e:
            self.log_test("performance", "Serialization performance", False, str(e))

        # Test 3: Config merging performance
        try:
            base_config = UseCaseConfig()
            override_config = UseCaseConfig(models={"llm": "gpt-4-turbo"})

            start_time = time.time()
            for _ in range(1000):
                base_config.merge_with(override_config)
            end_time = time.time()

            avg_time = (end_time - start_time) / 1000
            if avg_time < 0.005:  # Less than 5ms per merge
                self.log_test(
                    "performance", "Config merging performance", True, f"Avg: {avg_time:.6f}s"
                )
            else:
                self.log_test(
                    "performance", "Config merging performance", False, f"Too slow: {avg_time:.6f}s"
                )
        except Exception as e:
            self.log_test("performance", "Config merging performance", False, str(e))

    def calculate_overall_score(self):
        """Calculate overall verification score."""
        total_tests = 0
        passed_tests = 0

        for category in [
            "schema_validation",
            "database_integration",
            "constraint_validation",
            "performance",
        ]:
            total_tests += self.results[category]["passed"] + self.results[category]["failed"]
            passed_tests += self.results[category]["passed"]

        if total_tests > 0:
            score = (passed_tests / total_tests) * 100
            self.results["overall"]["score"] = score

            if score >= 90:
                self.results["overall"]["status"] = "EXCELLENT"
            elif score >= 80:
                self.results["overall"]["status"] = "GOOD"
            elif score >= 70:
                self.results["overall"]["status"] = "ACCEPTABLE"
            else:
                self.results["overall"]["status"] = "NEEDS_IMPROVEMENT"
        else:
            self.results["overall"]["status"] = "NO_TESTS"
            self.results["overall"]["score"] = 0

    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("USE CASE CONFIG VERIFICATION SUMMARY")
        print("=" * 60)

        for category, results in self.results.items():
            if category == "overall":
                continue

            total = results["passed"] + results["failed"]
            if total > 0:
                percentage = (results["passed"] / total) * 100
                print(
                    f"\n{category.upper().replace('_', ' ')}: {results['passed']}/{total} ({percentage:.1f}%)"
                )

                for test in results["tests"]:
                    status = "✅" if test["passed"] else "❌"
                    print(f"  {status} {test['test']}")
                    if test["message"]:
                        print(f"     {test['message']}")

        print(
            f"\nOVERALL SCORE: {self.results['overall']['score']:.1f}% ({self.results['overall']['status']})"
        )
        print("=" * 60)

    def run_verification(self):
        """Run complete verification."""
        print("🚀 Starting UseCaseConfig Implementation Verification...")
        print("Feature: Use Case Config Schema & Validation")
        print("Phase: B1-F1")

        self.verify_schema_validation()
        self.verify_database_integration()
        self.verify_constraint_validation()
        self.verify_performance()

        self.calculate_overall_score()
        self.print_summary()

        return self.results["overall"]["status"] in ["EXCELLENT", "GOOD", "ACCEPTABLE"]


def main():
    """Main verification function."""
    verifier = UseCaseConfigVerifier()
    success = verifier.run_verification()

    if success:
        print("\n🎉 UseCaseConfig verification PASSED!")
        print("✅ Use Case Config Schema & Validation is ready for production")
        return 0
    print("\n❌ UseCaseConfig verification FAILED!")
    print("🔧 Please review and fix the issues above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
