#!/usr/bin/env python3
"""
Full Test Suite Runner for Cyber Defense Analyst AI Assistant

This script orchestrates the entire test process:
1. Sets up the test environment with dependencies and configurations
2. Fixes import issues and repository method signatures
3. Runs the comprehensive test suite with coverage analysis
4. Generates detailed reports of the results

Usage:
    python scripts/testing/run_tests.py [--component COMPONENT] [--verbose] [--skip-setup] [--skip-fixes]

Options:
    --component COMPONENT    Run tests only for a specific component (backend, embedding, retrieval)
    --verbose                Enable verbose output for all steps
    --skip-setup             Skip the environment setup step
    --skip-fixes             Skip the import fixes step
    --fail-under PERCENTAGE  Exit with error if coverage is below specified percentage
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Define directories
SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPTS_DIR.parent.parent  # This should be /workspace

# Define script paths
SETUP_SCRIPT = SCRIPTS_DIR / "setup_environment.py"
IMPORT_FIX_SCRIPT = SCRIPTS_DIR / "fix_imports.py"
COMPREHENSIVE_TESTS_SCRIPT = SCRIPTS_DIR / "run_coverage.py"

# Custom test scripts
EMBEDDING_CLIENT_TEST = BASE_DIR / "tests" / "embedding" / "unit" / "test_embedding_client.py"
VECTOR_REPOSITORY_TEST = BASE_DIR / "tests" / "retrieval" / "unit" / "test_vector_repository.py"


def run_script(script_path: Path, args: list[str], verbose: bool = False) -> tuple[int, str, str]:
    """Run a Python script with the given arguments."""
    cmd = [sys.executable, str(script_path), *args]
    if verbose:
        print(f"Running: {' '.join(cmd)}")

    start_time = time.time()
    process = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    # Print the output based on verbosity
    if verbose or process.returncode != 0:
        print(
            f"\nCommand completed in {duration:.2f} seconds with return code {process.returncode}"
        )
        print("\nSTDOUT:")
        print(process.stdout)

        if process.stderr:
            print("\nSTDERR:")
            print(process.stderr)
    else:
        # Print just a summary
        lines = process.stdout.strip().split("\n")
        summary_lines = [
            line for line in lines if "=" in line or "PASSED" in line or "FAILED" in line
        ]
        if summary_lines:
            print("\n".join(summary_lines[-5:]))

    return process.returncode, process.stdout, process.stderr


def setup_environment(component: str | None, verbose: bool) -> bool:
    """Run the setup environment script."""
    print("\n\n" + "=" * 80)
    print(" Setting Up Test Environment ".center(80, "="))
    print("=" * 80 + "\n")

    args = []
    if component:
        args.extend(["--component", component])
    if verbose:
        args.append("--verbose")

    # Run with --skip-deps to avoid reinstalling dependencies if they're already there
    # Can be overridden by appending --force to the command
    args.append("--skip-deps")

    returncode, _, _ = run_script(SETUP_SCRIPT, args, verbose)
    return returncode == 0


def fix_imports(component: str | None, verbose: bool) -> bool:
    """Run the import fix script."""
    print("\n\n" + "=" * 80)
    print(" Fixing Import Issues ".center(80, "="))
    print("=" * 80 + "\n")

    args = ["--fix-repo-methods"]
    if component:
        args.extend(["--component", component])
    if verbose:
        args.append("--verbose")

    returncode, _, _ = run_script(IMPORT_FIX_SCRIPT, args, verbose)
    return returncode == 0


def run_component_tests(component: str, verbose: bool) -> bool:
    """Run specific component tests."""
    print("\n\n" + "=" * 80)
    print(f" Running {component.upper()} Specific Tests ".center(80, "="))
    print("=" * 80 + "\n")

    success = True

    if component == "embedding" and EMBEDDING_CLIENT_TEST.exists():
        # Run embedding client tests
        print(f"Running embedding client tests: {EMBEDDING_CLIENT_TEST}")
        returncode, _, _ = run_script(EMBEDDING_CLIENT_TEST, ["-v"] if verbose else [], verbose)
        success = success and (returncode == 0)

    if component == "retrieval" and VECTOR_REPOSITORY_TEST.exists():
        # Run vector repository tests
        print(f"Running vector repository tests: {VECTOR_REPOSITORY_TEST}")
        returncode, _, _ = run_script(VECTOR_REPOSITORY_TEST, ["-v"] if verbose else [], verbose)
        success = success and (returncode == 0)

    return success


def run_comprehensive_tests(component: str | None, verbose: bool, fail_under: int | None) -> bool:
    """Run the comprehensive test script."""
    print("\n\n" + "=" * 80)
    print(" Running Comprehensive Tests ".center(80, "="))
    print("=" * 80 + "\n")

    args = ["--html", "--xml"]
    if component:
        args.extend(["--component", component])
    if verbose:
        args.append("--verbose")
    if fail_under is not None:
        args.extend(["--fail-under", str(fail_under)])

    returncode, _, _ = run_script(COMPREHENSIVE_TESTS_SCRIPT, args, verbose)
    return returncode == 0


def check_reports() -> dict[str, Any]:
    """Check for generated reports and summarize them."""
    coverage_dir = BASE_DIR / "coverage_reports"
    report_files = list(coverage_dir.glob("**/report.md"))
    detailed_report = coverage_dir / "detailed_report.md"

    return {
        "coverage_dir": coverage_dir,
        "report_files": report_files,
        "detailed_report": detailed_report if detailed_report.exists() else None,
        "html_reports": list(coverage_dir.glob("**/html/index.html")),
        "xml_reports": list(coverage_dir.glob("**/coverage.xml")),
    }


def summarize_results(component: str | None, reports: dict[str, Any]) -> None:
    """Print a summary of the test results."""
    print("\n\n" + "=" * 80)
    print(" Test Results Summary ".center(80, "="))
    print("=" * 80 + "\n")

    if reports["detailed_report"]:
        # Try to extract coverage percentage from the detailed report
        with open(reports["detailed_report"]) as f:
            content = f.read()
            import re

            coverage_match = re.search(r"Overall Coverage\*\*:\s*([\d\.]+)%", content)
            if coverage_match:
                coverage = float(coverage_match.group(1))
                print(f"Overall coverage: {coverage:.2f}%")

    print(f"\nDetailed reports are available in: {reports['coverage_dir']}")

    if reports["html_reports"]:
        print("\nHTML coverage reports:")
        for report in reports["html_reports"]:
            print(f"  - {report}")

    if reports["report_files"]:
        print("\nMarkdown summary reports:")
        for report in reports["report_files"]:
            print(f"  - {report}")


def main():
    """Main function to run the full test suite."""
    parser = argparse.ArgumentParser(description="Run the full test suite")
    parser.add_argument(
        "--component",
        choices=["backend", "embedding", "retrieval"],
        help="Component to run tests for",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--skip-setup", action="store_true", help="Skip environment setup")
    parser.add_argument("--skip-fixes", action="store_true", help="Skip import fixes")
    parser.add_argument(
        "--fail-under",
        type=int,
        help="Exit with error if coverage is below specified percentage",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(" Full Test Suite Runner ".center(80, "="))
    print("=" * 80 + "\n")

    if args.component:
        print(f"Running tests for component: {args.component.upper()}")
    else:
        print("Running tests for ALL COMPONENTS")

    print(f"Base directory: {BASE_DIR}")
    print(f"Scripts directory: {SCRIPTS_DIR}")
    print("")

    # Run each step of the process
    success = True

    # Step 1: Setup environment (if not skipped)
    if not args.skip_setup:
        success = success and setup_environment(args.component, args.verbose)
        if not success:
            print("Environment setup failed, aborting.")
            return 1
    else:
        print("Skipping environment setup as requested.")

    # Step 2: Fix imports (if not skipped)
    if not args.skip_fixes:
        success = success and fix_imports(args.component, args.verbose)
        if not success:
            print("Import fixes failed, proceeding with caution.")
            # Don't abort, just warn
    else:
        print("Skipping import fixes as requested.")

    # Step 3: Run component-specific tests (if applicable)
    if args.component:
        success = success and run_component_tests(args.component, args.verbose)
        if not success:
            print(f"Component-specific tests for {args.component} failed, proceeding with caution.")
            # Don't abort, run comprehensive tests anyway

    # Step 4: Run comprehensive tests
    success = success and run_comprehensive_tests(args.component, args.verbose, args.fail_under)
    if not success:
        print("Comprehensive tests failed.")
        # Don't abort, still want to show reports

    # Step 5: Check for reports and summarize
    reports = check_reports()
    summarize_results(args.component, reports)

    # Return appropriate exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
