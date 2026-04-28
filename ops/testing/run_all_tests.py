#!/usr/bin/env python3
"""
Centralized Test Runner for AI Operations Platform

This script provides a unified interface for running all tests across the project,
including unit tests, integration tests, and end-to-end tests.

Requires: Run with the project virtual environment activated (Python 3.12).
  source .venv/bin/activate   # or venv/bin/activate
  python ops/testing/run_all_tests.py [options]

Usage:
    python ops/testing/run_all_tests.py [options]

Options:
    --component COMPONENT    Run tests for specific component (orchestrator, corpus_svc, embedding, inference-gateway, llm_guard_svc, shared, frontend, integration, e2e, all)
    --type TYPE             Run specific test type (unit, integration, e2e, all)
    --coverage              Generate coverage report
    --verbose               Enable verbose output
    --parallel              Run tests in parallel
    --fail-fast             Stop on first failure
    --html-report           Generate HTML coverage report
    --threshold PERCENT     Fail if coverage below threshold
    --help                  Show this help message

Examples:
    # Run all tests
    python scripts/testing/run_all_tests.py

    # Run orchestrator tests only
    python scripts/testing/run_all_tests.py --component orchestrator

    # Run integration tests with coverage
    python scripts/testing/run_all_tests.py --type integration --coverage

    # Run all tests with HTML coverage report
    python scripts/testing/run_all_tests.py --coverage --html-report
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load test environment variables
from load_test_env import load_test_env

load_test_env()


class TestRunner:
    """Centralized test runner for the AI Operations Platform project."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.src_dir = self.project_root / "src"
        self.tests_dir = self.project_root / "tests"
        # Use same Python as this process (venv if activated); project requires 3.12
        self.python = sys.executable
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "coverage": 0.0,
        }

    def run_command(self, cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, and stderr."""
        if cwd is None:
            cwd = self.project_root

        # Inherit environment (including OPENBLAS_NUM_THREADS=1 from setup_environment)
        env = os.environ.copy()

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 5 minutes"
        except Exception as e:
            return 1, "", str(e)

    def setup_environment(self) -> bool:
        """Set up test environment."""
        print("🔧 Setting up test environment...")

        # Set environment variables
        env_vars = {
            "TESTING": "true",
            "PYTHONPATH": str(self.src_dir),
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "test_password_123",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "aio-test",
            "DATABASE_URL": "postgresql+psycopg://testuser:test_password_123@localhost:5433/aio-test",
            "OPENAI_API_KEY": "test_openai_api_key_for_tests",
            # Prevent OpenBLAS segfaults on macOS ARM64 (numpy.linalg crashes)
            "OPENBLAS_NUM_THREADS": "1",
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        print("✅ Environment variables set")
        return True

    def run_service_tests(
        self, service: str, coverage: bool = False, verbose: bool = False
    ) -> bool:
        """Run tests for a specific service."""
        print(f"🧪 Running {service} tests...")

        service_dir = self.src_dir / service
        if not service_dir.exists():
            print(f"❌ Service directory not found: {service_dir}")
            return False

        # Check if service has run_tests.sh
        test_script = service_dir / "run_tests.sh"
        tests_dir = service_dir / "tests"
        if test_script.exists():
            cmd = ["bash", str(test_script)]
            if coverage:
                cmd.extend(["--cov=app", "--cov-report=term-missing"])
            if verbose:
                cmd.append("-v")
        elif tests_dir.exists():
            # Fallback to pytest (use same Python as runner, e.g. venv)
            cmd = [self.python, "-m", "pytest", str(tests_dir)]
            if coverage:
                cmd.extend(["--cov=app", "--cov-report=term-missing"])
            if verbose:
                cmd.append("-v")
        else:
            print(f"⏭️  No tests for {service} (no run_tests.sh or tests/)")
            return True

        exit_code, stdout, stderr = self.run_command(cmd, cwd=service_dir)

        if exit_code == 0:
            print(f"✅ {service} tests passed")
            self._parse_test_results(stdout)
        else:
            print(f"❌ {service} tests failed")
            if verbose:
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")

        return exit_code == 0

    def run_integration_tests(self, coverage: bool = False, verbose: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running integration tests...")

        if not self.tests_dir.exists():
            print("❌ Tests directory not found")
            return False

        cmd = [self.python, "-m", "pytest", str(self.tests_dir / "integration")]
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])
        if verbose:
            cmd.append("-v")

        exit_code, stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print("✅ Integration tests passed")
            self._parse_test_results(stdout)
        else:
            print("❌ Integration tests failed")
            if verbose:
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")

        return exit_code == 0

    def run_e2e_tests(self, verbose: bool = False) -> bool:
        """Run end-to-end tests."""
        print("🌐 Running E2E tests...")

        if not self.tests_dir.exists():
            print("❌ Tests directory not found")
            return False

        cmd = [self.python, "-m", "pytest", str(self.tests_dir / "e2e")]
        if verbose:
            cmd.append("-v")

        exit_code, stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print("✅ E2E tests passed")
            self._parse_test_results(stdout)
        else:
            print("❌ E2E tests failed")
            if verbose:
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")

        return exit_code == 0

    def run_frontend_tests(self, verbose: bool = False) -> bool:
        """Run frontend tests."""
        print("🎨 Running frontend tests...")

        frontend_dir = self.src_dir / "frontend-angular"
        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return False

        # Run Angular tests
        cmd = ["npm", "test", "--", "--watch=false"]
        if verbose:
            cmd.append("--verbose")

        exit_code, stdout, stderr = self.run_command(cmd, cwd=frontend_dir)

        if exit_code == 0:
            print("✅ Frontend tests passed")
        else:
            print("❌ Frontend tests failed")
            if verbose:
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")

        return exit_code == 0

    def _parse_test_results(self, output: str):
        """Parse test results from pytest output."""
        lines = output.split("\n")
        for line in lines:
            if "passed" in line and "failed" in line:
                # Parse pytest summary line
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        if "passed" in line:
                            self.results["passed"] += int(part)
                        elif "failed" in line:
                            self.results["failed"] += int(part)
                        elif "skipped" in line:
                            self.results["skipped"] += int(part)
                        elif "error" in line:
                            self.results["errors"] += int(part)

    def generate_coverage_report(self, html: bool = False) -> bool:
        """Generate coverage report."""
        print("📊 Generating coverage report...")

        cmd = [self.python, "-m", "pytest", "--cov=src", "--cov-report=term-missing"]
        if html:
            cmd.append("--cov-report=html")

        exit_code, _stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print("✅ Coverage report generated")
            if html:
                print("📄 HTML report available at htmlcov/index.html")
        else:
            print("❌ Failed to generate coverage report")
            print(f"STDERR: {stderr}")

        return exit_code == 0

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏭️  Skipped: {self.results['skipped']}")
        print(f"💥 Errors: {self.results['errors']}")
        if self.results["coverage"] > 0:
            print(f"📊 Coverage: {self.results['coverage']:.1f}%")
        print("=" * 50)

    def run_tests(
        self,
        component: str = "all",
        test_type: str = "all",
        coverage: bool = False,
        verbose: bool = False,
        parallel: bool = False,
        fail_fast: bool = False,
        html_report: bool = False,
        threshold: float | None = None,
    ) -> bool:
        """Run tests based on specified options."""

        print("🚀 Starting AI Operations Platform Test Suite")
        print(f"Component: {component}, Type: {test_type}")
        print("-" * 50)

        # Setup environment
        if not self.setup_environment():
            return False

        success = True
        start_time = time.time()

        try:
            # Run tests based on component
            if component in ["all", "orchestrator"]:
                success &= self.run_service_tests("orchestrator", coverage, verbose)
            if component in ["all", "corpus_svc"]:
                success &= self.run_service_tests("corpus_svc", coverage, verbose)
            if component in ["all", "embedding"]:
                success &= self.run_service_tests("embedding", coverage, verbose)
            if component in ["all", "inference-gateway"]:
                success &= self.run_service_tests("inference-gateway", coverage, verbose)
            if component in ["all", "llm_guard_svc"]:
                success &= self.run_service_tests("llm_guard_svc", coverage, verbose)
            if component in ["all", "shared"]:
                success &= self.run_service_tests("shared", coverage, verbose)
            if component in ["all", "frontend"]:
                success &= self.run_frontend_tests(verbose)
            if component in ["all", "integration"]:
                success &= self.run_integration_tests(coverage, verbose)
            if component in ["all", "e2e"]:
                success &= self.run_e2e_tests(verbose)

            # Generate coverage report if requested
            if coverage and component == "all":
                self.generate_coverage_report(html_report)

            # Check coverage threshold
            if threshold and self.results["coverage"] < threshold:
                print(
                    f"❌ Coverage {self.results['coverage']:.1f}% is below threshold {threshold}%"
                )
                success = False

        except KeyboardInterrupt:
            print("\n⏹️  Test execution interrupted by user")
            success = False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            success = False

        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n⏱️  Total execution time: {duration:.2f} seconds")
        self.print_summary()

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Centralized Test Runner for AI Operations Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--component",
        choices=[
            "orchestrator",
            "corpus_svc",
            "embedding",
            "inference-gateway",
            "llm_guard_svc",
            "shared",
            "frontend",
            "integration",
            "e2e",
            "all",
        ],
        default="all",
        help="Run tests for specific component",
    )

    parser.add_argument(
        "--type",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Run specific test type",
    )

    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")

    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")

    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")

    parser.add_argument(
        "--threshold", type=float, help="Fail if coverage below threshold percentage"
    )

    args = parser.parse_args()

    # Create and run test runner
    runner = TestRunner()
    success = runner.run_tests(
        component=args.component,
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        parallel=args.parallel,
        fail_fast=args.fail_fast,
        html_report=args.html_report,
        threshold=args.threshold,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
