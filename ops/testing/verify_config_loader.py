#!/usr/bin/env python3
"""
Verification script for B1-F2: Use Case Config Loader Service

This script validates the complete implementation of B1-F2 including:
- Config loading by use_case_id
- Config loading by intent_type
- Caching functionality
- Database integration
- Error handling
- Performance characteristics

This is a permanent testing utility that should be run as part of the
test suite to validate the UseCaseConfigLoader implementation.

Usage:
    python scripts/testing/verify_config_loader.py
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
from src.backend.app.schemas.intent import RequestType
from src.backend.app.schemas.use_case_config import UseCaseConfig
from src.backend.app.services.use_case_config_loader import (
    UseCaseConfigLoader,
    clear_global_cache,
    get_config_loader,
)


class ConfigLoaderVerifier:
    """Verification class for UseCaseConfigLoader implementation."""

    def __init__(self):
        self.results = {
            "config_loading": {"passed": 0, "failed": 0, "tests": []},
            "caching": {"passed": 0, "failed": 0, "tests": []},
            "database_integration": {"passed": 0, "failed": 0, "tests": []},
            "error_handling": {"passed": 0, "failed": 0, "tests": []},
            "performance": {"passed": 0, "failed": 0, "tests": []},
            "overall": {"status": "PENDING", "score": 0},
        }
        self.db_session = None
        self.test_use_cases = []

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

    def setup_test_data(self):
        """Set up test data in database."""
        try:
            self.db_session = SessionLocal()

            # Create test use cases
            test_configs = [
                {
                    "use_case_id": "verify_config_loader_test_1",
                    "name": "Config Loader Test 1",
                    "description": "Test use case for config loader verification",
                    "category": "test",
                    "intent_type": "QUERY",
                    "is_active": True,
                    "config_json": {
                        "visibility": {"roles": ["analyst"], "tags": ["test"]},
                        "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
                        "generation_params": {"temperature": 0.7, "max_tokens": 1024},
                        "rag": {"enabled": True, "top_k": 10, "vector_collections": ["documents"]},
                        "output_contract": {"format": "text"},
                        "telemetry": {"required_metrics": ["retrieval"]},
                        "policy": {"streaming_enabled": True},
                        "tools_allowlist": ["web_search"],
                    },
                    "created_by_user_id": None,
                },
                {
                    "use_case_id": "verify_config_loader_test_2",
                    "name": "Config Loader Test 2",
                    "description": "Second test use case for config loader verification",
                    "category": "test",
                    "intent_type": "SUMMARIZATION",
                    "is_active": True,
                    "config_json": {
                        "visibility": {"roles": ["analyst", "admin"], "tags": ["summarization"]},
                        "models": {"llm": "gpt-4-turbo", "embedding": "text-embedding-3-large"},
                        "generation_params": {"temperature": 0.3, "max_tokens": 2048},
                        "rag": {
                            "enabled": True,
                            "top_k": 5,
                            "vector_collections": ["documents", "summaries"],
                        },
                        "output_contract": {"format": "json"},
                        "telemetry": {"required_metrics": ["retrieval", "model"]},
                        "policy": {"streaming_enabled": True, "streaming_default": True},
                        "tools_allowlist": [],
                    },
                    "created_by_user_id": None,
                },
                {
                    "use_case_id": "verify_config_loader_test_inactive",
                    "name": "Config Loader Test Inactive",
                    "description": "Inactive test use case",
                    "category": "test",
                    "intent_type": "RULE_GENERATION",
                    "is_active": False,
                    "config_json": {
                        "visibility": {"roles": ["analyst"], "tags": ["rule_generation"]},
                        "models": {"llm": "gpt-4o"},
                        "generation_params": {"temperature": 0.2},
                        "rag": {"enabled": True, "top_k": 3},
                        "output_contract": {"format": "json"},
                        "telemetry": {"required_metrics": ["retrieval"]},
                        "policy": {"streaming_enabled": False},
                        "tools_allowlist": [],
                    },
                    "created_by_user_id": None,
                },
            ]

            for config_data in test_configs:
                use_case = UseCase(**config_data)
                self.db_session.add(use_case)
                self.test_use_cases.append(use_case)

            self.db_session.commit()

            for use_case in self.test_use_cases:
                self.db_session.refresh(use_case)

            return True

        except Exception as e:
            self.log_test("database_integration", "Test data setup", False, str(e))
            return False

    def cleanup_test_data(self):
        """Clean up test data from database."""
        try:
            if self.db_session:
                for use_case in self.test_use_cases:
                    self.db_session.delete(use_case)
                self.db_session.commit()
                self.db_session.close()
            return True
        except Exception as e:
            print(f"Warning: Failed to cleanup test data: {e!s}")
            return False

    def verify_config_loading(self):
        """Verify config loading functionality."""
        print("\n🔍 Testing Config Loading...")

        try:
            loader = UseCaseConfigLoader(self.db_session)

            # Test 1: Load config by use_case_id
            config = loader.load_config("verify_config_loader_test_1")
            if config and config.models.llm == "gpt-4o" and config.rag.top_k == 10:
                self.log_test("config_loading", "Load config by use_case_id", True)
            else:
                self.log_test(
                    "config_loading",
                    "Load config by use_case_id",
                    False,
                    "Config not loaded correctly",
                )

            # Test 2: Load config by intent_type
            config = loader.load_config_by_intent(RequestType.QUERY)
            if config and config.models.llm == "gpt-4o":
                self.log_test("config_loading", "Load config by intent_type", True)
            else:
                self.log_test(
                    "config_loading",
                    "Load config by intent_type",
                    False,
                    "Config not loaded correctly",
                )

            # Test 3: Load config for different intent
            config = loader.load_config_by_intent(RequestType.SUMMARIZATION)
            if (
                config
                and config.models.llm == "gpt-4-turbo"
                and config.generation_params.temperature == 0.3
            ):
                self.log_test("config_loading", "Load config for different intent", True)
            else:
                self.log_test(
                    "config_loading",
                    "Load config for different intent",
                    False,
                    "Config not loaded correctly",
                )

            # Test 4: Load non-existent config
            config = loader.load_config("nonexistent_use_case")
            if config is None:
                self.log_test("config_loading", "Load non-existent config returns None", True)
            else:
                self.log_test(
                    "config_loading",
                    "Load non-existent config returns None",
                    False,
                    "Should return None",
                )

            # Test 5: Load inactive use case
            config = loader.load_config("verify_config_loader_test_inactive")
            if config is None:
                self.log_test("config_loading", "Load inactive use case returns None", True)
            else:
                self.log_test(
                    "config_loading",
                    "Load inactive use case returns None",
                    False,
                    "Should return None",
                )

        except Exception as e:
            self.log_test("config_loading", "Config loading", False, str(e))

    def verify_caching(self):
        """Verify caching functionality."""
        print("\n🔍 Testing Caching...")

        try:
            loader = UseCaseConfigLoader(self.db_session)

            # Test 1: Cache hit for use_case_id
            config1 = loader.load_config("verify_config_loader_test_1")
            config2 = loader.load_config("verify_config_loader_test_1")
            if config1 is config2:  # Same object (cached)
                self.log_test("caching", "Cache hit for use_case_id", True)
            else:
                self.log_test("caching", "Cache hit for use_case_id", False, "Config not cached")

            # Test 2: Cache hit for intent_type
            config1 = loader.load_config_by_intent(RequestType.QUERY)
            config2 = loader.load_config_by_intent(RequestType.QUERY)
            if config1 is config2:  # Same object (cached)
                self.log_test("caching", "Cache hit for intent_type", True)
            else:
                self.log_test("caching", "Cache hit for intent_type", False, "Config not cached")

            # Test 3: Cache invalidation
            loader.invalidate_cache(use_case_id="verify_config_loader_test_1")
            if "verify_config_loader_test_1" not in loader._cache:
                self.log_test("caching", "Cache invalidation by use_case_id", True)
            else:
                self.log_test(
                    "caching", "Cache invalidation by use_case_id", False, "Cache not invalidated"
                )

            # Test 4: Cache stats
            stats = loader.get_cache_stats()
            if isinstance(stats, dict) and "use_case_cache_size" in stats:
                self.log_test("caching", "Cache stats", True)
            else:
                self.log_test("caching", "Cache stats", False, "Invalid cache stats")

            # Test 5: Clear cache
            loader.clear_cache()
            if len(loader._cache) == 0 and len(loader._cache_by_intent) == 0:
                self.log_test("caching", "Clear cache", True)
            else:
                self.log_test("caching", "Clear cache", False, "Cache not cleared")

        except Exception as e:
            self.log_test("caching", "Caching", False, str(e))

    def verify_database_integration(self):
        """Verify database integration."""
        print("\n🔍 Testing Database Integration...")

        try:
            loader = UseCaseConfigLoader(self.db_session)

            # Test 1: Load config from database
            config = loader.load_config("verify_config_loader_test_1")
            if config and config.models.llm == "gpt-4o":
                self.log_test("database_integration", "Load config from database", True)
            else:
                self.log_test(
                    "database_integration",
                    "Load config from database",
                    False,
                    "Config not loaded from DB",
                )

            # Test 2: Load config by intent from database
            config = loader.load_config_by_intent(RequestType.SUMMARIZATION)
            if config and config.models.llm == "gpt-4-turbo":
                self.log_test("database_integration", "Load config by intent from database", True)
            else:
                self.log_test(
                    "database_integration",
                    "Load config by intent from database",
                    False,
                    "Config not loaded from DB",
                )

            # Test 3: Preload configs
            loader.preload_configs(
                use_case_ids=["verify_config_loader_test_1", "verify_config_loader_test_2"],
                intent_types=[RequestType.QUERY, RequestType.SUMMARIZATION],
            )
            stats = loader.get_cache_stats()
            if stats["use_case_cache_size"] >= 2 and stats["intent_cache_size"] >= 2:
                self.log_test("database_integration", "Preload configs", True)
            else:
                self.log_test(
                    "database_integration", "Preload configs", False, "Configs not preloaded"
                )

        except Exception as e:
            self.log_test("database_integration", "Database integration", False, str(e))

    def verify_error_handling(self):
        """Verify error handling."""
        print("\n🔍 Testing Error Handling...")

        try:
            loader = UseCaseConfigLoader(self.db_session)

            # Test 1: Empty use_case_id
            try:
                loader.load_config("")
                self.log_test(
                    "error_handling",
                    "Empty use_case_id raises ValueError",
                    False,
                    "Should have raised ValueError",
                )
            except ValueError:
                self.log_test("error_handling", "Empty use_case_id raises ValueError", True)

            # Test 2: None use_case_id
            try:
                loader.load_config(None)
                self.log_test(
                    "error_handling",
                    "None use_case_id raises ValueError",
                    False,
                    "Should have raised ValueError",
                )
            except ValueError:
                self.log_test("error_handling", "None use_case_id raises ValueError", True)

            # Test 3: None intent_type
            try:
                loader.load_config_by_intent(None)
                self.log_test(
                    "error_handling",
                    "None intent_type raises ValueError",
                    False,
                    "Should have raised ValueError",
                )
            except ValueError:
                self.log_test("error_handling", "None intent_type raises ValueError", True)

            # Test 4: Get default config
            config = loader.get_default_config()
            if config and isinstance(config, UseCaseConfig):
                self.log_test("error_handling", "Get default config", True)
            else:
                self.log_test(
                    "error_handling", "Get default config", False, "Default config not returned"
                )

        except Exception as e:
            self.log_test("error_handling", "Error handling", False, str(e))

    def verify_performance(self):
        """Verify performance characteristics."""
        print("\n🔍 Testing Performance...")

        try:
            loader = UseCaseConfigLoader(self.db_session)

            # Test 1: Config loading performance
            start_time = time.time()
            for _ in range(100):
                loader.load_config("verify_config_loader_test_1")
            end_time = time.time()

            avg_time = (end_time - start_time) / 100
            if avg_time < 0.01:  # Less than 10ms per load
                self.log_test(
                    "performance", "Config loading performance", True, f"Avg: {avg_time:.6f}s"
                )
            else:
                self.log_test(
                    "performance", "Config loading performance", False, f"Too slow: {avg_time:.6f}s"
                )

            # Test 2: Cache hit performance
            start_time = time.time()
            for _ in range(1000):
                loader.load_config("verify_config_loader_test_1")  # Should hit cache
            end_time = time.time()

            avg_time = (end_time - start_time) / 1000
            if avg_time < 0.001:  # Less than 1ms per cache hit
                self.log_test("performance", "Cache hit performance", True, f"Avg: {avg_time:.6f}s")
            else:
                self.log_test(
                    "performance", "Cache hit performance", False, f"Too slow: {avg_time:.6f}s"
                )

            # Test 3: Preload performance
            loader.clear_cache()
            start_time = time.time()
            loader.preload_configs(
                use_case_ids=["verify_config_loader_test_1", "verify_config_loader_test_2"],
                intent_types=[RequestType.QUERY, RequestType.SUMMARIZATION],
            )
            end_time = time.time()

            preload_time = end_time - start_time
            if preload_time < 1.0:  # Less than 1 second for preload
                self.log_test(
                    "performance", "Preload performance", True, f"Time: {preload_time:.3f}s"
                )
            else:
                self.log_test(
                    "performance", "Preload performance", False, f"Too slow: {preload_time:.3f}s"
                )

        except Exception as e:
            self.log_test("performance", "Performance", False, str(e))

    def verify_global_functions(self):
        """Verify global config loader functions."""
        print("\n🔍 Testing Global Functions...")

        try:
            # Test 1: get_config_loader without cache
            loader1 = get_config_loader(self.db_session)
            if isinstance(loader1, UseCaseConfigLoader):
                self.log_test("config_loading", "get_config_loader without cache", True)
            else:
                self.log_test(
                    "config_loading",
                    "get_config_loader without cache",
                    False,
                    "Invalid loader type",
                )

            # Test 2: get_config_loader with cache
            loader2 = get_config_loader(self.db_session, "test_cache_key")
            loader3 = get_config_loader(self.db_session, "test_cache_key")
            if loader2 is loader3:  # Same object (cached)
                self.log_test("config_loading", "get_config_loader with cache", True)
            else:
                self.log_test(
                    "config_loading", "get_config_loader with cache", False, "Loader not cached"
                )

            # Test 3: clear_global_cache
            clear_global_cache()
            loader4 = get_config_loader(self.db_session, "test_cache_key")
            if loader4 is not loader2:  # Different object (cache cleared)
                self.log_test("config_loading", "clear_global_cache", True)
            else:
                self.log_test(
                    "config_loading", "clear_global_cache", False, "Global cache not cleared"
                )

        except Exception as e:
            self.log_test("config_loading", "Global functions", False, str(e))

    def calculate_overall_score(self):
        """Calculate overall verification score."""
        total_tests = 0
        passed_tests = 0

        for category in [
            "config_loading",
            "caching",
            "database_integration",
            "error_handling",
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
        print("USE CASE CONFIG LOADER VERIFICATION SUMMARY")
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
        print("🚀 Starting UseCaseConfigLoader Implementation Verification...")
        print("Feature: Use Case Config Loader Service")
        print("Phase: B1-F2")

        # Setup test data
        if not self.setup_test_data():
            print("❌ Failed to setup test data. Aborting verification.")
            return False

        try:
            self.verify_config_loading()
            self.verify_caching()
            self.verify_database_integration()
            self.verify_error_handling()
            self.verify_performance()
            self.verify_global_functions()

            self.calculate_overall_score()
            self.print_summary()

            return self.results["overall"]["status"] in ["EXCELLENT", "GOOD", "ACCEPTABLE"]

        finally:
            # Cleanup test data
            self.cleanup_test_data()


def main():
    """Main verification function."""
    verifier = ConfigLoaderVerifier()
    success = verifier.run_verification()

    if success:
        print("\n🎉 UseCaseConfigLoader verification PASSED!")
        print("✅ Use Case Config Loader Service is ready for production")
        return 0
    print("\n❌ UseCaseConfigLoader verification FAILED!")
    print("🔧 Please review and fix the issues above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
