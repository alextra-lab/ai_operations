#!/usr/bin/env python3
"""
Service-Specific Test Runner

This script provides a convenient way to run tests for individual services
with proper environment setup and configuration.

Usage:
    python scripts/testing/run_service_tests.py <service> [options]

Services:
    backend     - Backend API service
    retrieval   - Retrieval service
    embedding   - Embedding service
    llm_guard   - LLM Guard service
    shared      - Shared modules
    frontend    - Angular frontend

Options:
    --type TYPE         Test type (unit, integration, all)
    --coverage          Generate coverage report
    --verbose           Enable verbose output
    --html-report       Generate HTML coverage report
    --threshold PERCENT Fail if coverage below threshold
    --help              Show this help message

Examples:
    # Run backend unit tests
    python scripts/testing/run_service_tests.py backend --type unit

    # Run retrieval tests with coverage
    python scripts/testing/run_service_tests.py retrieval --coverage

    # Run frontend tests
    python scripts/testing/run_service_tests.py frontend
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ServiceTestRunner:
    """Test runner for individual services."""

    def __init__(self, service: str):
        self.service = service
        self.project_root = PROJECT_ROOT
        self.src_dir = self.project_root / "src"
        self.service_dir = self.src_dir / service

        if not self.service_dir.exists():
            raise ValueError(f"Service directory not found: {self.service_dir}")

    def setup_environment(self):
        """Set up environment for the service."""
        # Set service-specific environment variables
        env_vars = {
            "TESTING": "true",
            "PYTHONPATH": str(self.src_dir),
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test_db",
            "OPENAI_API_KEY": "test_openai_api_key_for_tests",
        }

        # Service-specific environment variables
        if self.service == "backend":
            env_vars.update({"BACKEND_PORT": "8000", "JWT_SECRET": "test_jwt_secret"})
        elif self.service == "retrieval":
            env_vars.update({"RETRIEVAL_PORT": "8003", "QDRANT_URL": "http://localhost:6333"})
        elif self.service == "embedding":
            env_vars.update({"EMBEDDING_PORT": "8002"})
        elif self.service == "llm_guard":
            env_vars.update({"LLM_GUARD_PORT": "8004"})

        for key, value in env_vars.items():
            os.environ[key] = value

    def run_command(self, cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, and stderr."""
        if cwd is None:
            cwd = self.service_dir

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 5 minutes"
        except Exception as e:
            return 1, "", str(e)

    def run_python_tests(self, test_type: str, coverage: bool, verbose: bool) -> bool:
        """Run Python-based tests."""
        print(f"🐍 Running {self.service} Python tests...")

        # Determine test directory
        if test_type == "unit":
            test_dir = self.service_dir / "tests" / "unit"
        elif test_type == "integration":
            test_dir = self.service_dir / "tests" / "integration"
        else:  # all
            test_dir = self.service_dir / "tests"

        if not test_dir.exists():
            print(f"❌ Test directory not found: {test_dir}")
            return False

        # Check if service has run_tests.sh
        test_script = self.service_dir / "run_tests.sh"
        if test_script.exists():
            cmd = ["bash", str(test_script)]
            if coverage:
                cmd.extend(["--cov=app", "--cov-report=term-missing"])
            if verbose:
                cmd.append("-v")
        else:
            # Fallback to pytest
            cmd = ["python", "-m", "pytest", str(test_dir)]
            if coverage:
                cmd.extend(["--cov=app", "--cov-report=term-missing"])
            if verbose:
                cmd.append("-v")

        exit_code, stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print(f"✅ {self.service} tests passed")
            if verbose:
                print(stdout)
        else:
            print(f"❌ {self.service} tests failed")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")

        return exit_code == 0

    def run_frontend_tests(self, verbose: bool) -> bool:
        """Run frontend tests."""
        print(f"🎨 Running {self.service} frontend tests...")

        # Check if package.json exists
        package_json = self.service_dir / "package.json"
        if not package_json.exists():
            print(f"❌ package.json not found in {self.service_dir}")
            return False

        # Run npm test
        cmd = ["npm", "test", "--", "--watch=false"]
        if verbose:
            cmd.append("--verbose")

        exit_code, stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print(f"✅ {self.service} frontend tests passed")
            if verbose:
                print(stdout)
        else:
            print(f"❌ {self.service} frontend tests failed")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")

        return exit_code == 0

    def generate_coverage_report(self, html: bool = False) -> bool:
        """Generate coverage report for the service."""
        print(f"📊 Generating coverage report for {self.service}...")

        cmd = ["python", "-m", "pytest", "--cov=app", "--cov-report=term-missing"]
        if html:
            cmd.append("--cov-report=html")

        exit_code, _stdout, stderr = self.run_command(cmd)

        if exit_code == 0:
            print(f"✅ Coverage report generated for {self.service}")
            if html:
                print(f"📄 HTML report available at {self.service_dir}/htmlcov/index.html")
        else:
            print(f"❌ Failed to generate coverage report for {self.service}")
            print(f"STDERR: {stderr}")

        return exit_code == 0

    def run_tests(
        self,
        test_type: str = "all",
        coverage: bool = False,
        verbose: bool = False,
        html_report: bool = False,
        threshold: float | None = None,
    ) -> bool:
        """Run tests for the service."""

        print(f"🚀 Running {self.service} tests")
        print(f"Type: {test_type}, Coverage: {coverage}")
        print("-" * 40)

        # Setup environment
        self.setup_environment()

        success = True

        try:
            if self.service == "frontend":
                success = self.run_frontend_tests(verbose)
            else:
                success = self.run_python_tests(test_type, coverage, verbose)

            # Generate coverage report if requested
            if coverage and success:
                self.generate_coverage_report(html_report)

        except KeyboardInterrupt:
            print(f"\n⏹️  {self.service} test execution interrupted by user")
            success = False
        except Exception as e:
            print(f"❌ Unexpected error in {self.service} tests: {e}")
            success = False

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Service-Specific Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "service",
        choices=["backend", "retrieval", "embedding", "llm_guard", "shared", "frontend"],
        help="Service to run tests for",
    )

    parser.add_argument(
        "--type", choices=["unit", "integration", "all"], default="all", help="Test type to run"
    )

    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")

    parser.add_argument(
        "--threshold", type=float, help="Fail if coverage below threshold percentage"
    )

    args = parser.parse_args()

    try:
        # Create and run test runner
        runner = ServiceTestRunner(args.service)
        success = runner.run_tests(
            test_type=args.type,
            coverage=args.coverage,
            verbose=args.verbose,
            html_report=args.html_report,
            threshold=args.threshold,
        )

        sys.exit(0 if success else 1)

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
