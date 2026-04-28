#!/usr/bin/env python3
"""
Comprehensive Test Runner for Cyber Defense Analyst AI Assistant

This script runs a comprehensive test suite across all components:
1. Executes tests for specified components with coverage analysis
2. Generates coverage reports in various formats (terminal, HTML, XML)
3. Creates summary reports with test results and coverage metrics
4. Identifies areas for test improvement

Usage:
    python run_comprehensive_tests.py [--component COMPONENT] [--no-coverage] [--verbose]

Options:
    --component COMPONENT    Run tests only for a specific component (backend, embedding, retrieval)
    --no-coverage            Disable coverage reporting
    --verbose                Enable verbose output
    --html                   Generate HTML coverage reports
    --xml                    Generate XML coverage reports
    --fail-under PERCENTAGE  Exit with error if coverage is below specified percentage
"""

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Define base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # /workspace
SRC_DIR = BASE_DIR / "src"  # /workspace/src
TEST_DIR = BASE_DIR / "tests"  # /workspace/tests
COVERAGE_DIR = BASE_DIR / "coverage_reports"

# Define component directories and their corresponding source directories
COMPONENTS = {
    "backend": {
        "src_dir": SRC_DIR / "backend",
        "test_dir": TEST_DIR / "backend",
    },
    "embedding": {
        "src_dir": SRC_DIR / "embedding",
        "test_dir": TEST_DIR / "embedding",
    },
    "retrieval": {
        "src_dir": SRC_DIR / "retrieval",
        "test_dir": TEST_DIR / "retrieval",
    },
}

# Define integration tests directory
INTEGRATION_TEST_DIR = TEST_DIR / "integration"

# Default threshold for overall coverage
DEFAULT_COVERAGE_THRESHOLD = 60  # 60%


def ensure_directories_exist():
    """Ensure all necessary directories exist."""
    COVERAGE_DIR.mkdir(exist_ok=True)
    for component, _paths in COMPONENTS.items():
        component_coverage_dir = COVERAGE_DIR / component
        component_coverage_dir.mkdir(exist_ok=True)


def run_pytest(
    component: str | None,
    coverage: bool,
    verbose: bool,
    html: bool,
    xml: bool,
    fail_under: int | None,
) -> tuple[subprocess.CompletedProcess, float]:
    """Run pytest with appropriate parameters and return the process and coverage percentage."""
    # Base pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity if requested
    if verbose:
        cmd.append("-v")

    # Determine which tests to run
    if component:
        # Component-specific tests
        component_test_dir = COMPONENTS[component]["test_dir"]
        cmd.append(str(component_test_dir))

        # Also run integration tests that might involve this component
        if INTEGRATION_TEST_DIR.exists():
            cmd.append(str(INTEGRATION_TEST_DIR))
    else:
        # All tests
        cmd.append(str(TEST_DIR))

    # Add coverage options if enabled
    coverage_percentage = 0.0
    if coverage:
        # Base coverage options
        cmd.append("--cov")
        if component:
            # Component-specific coverage
            cmd.append(str(COMPONENTS[component]["src_dir"]))
        else:
            # Overall coverage
            cmd.append(str(SRC_DIR))

        # Add coverage report format options
        cmd.append("--cov-report=term")

        if html:
            if component:
                html_dir = str(COVERAGE_DIR / component / "html")
            else:
                html_dir = str(COVERAGE_DIR / "html")
            cmd.append(f"--cov-report=html:{html_dir}")

        if xml:
            if component:
                xml_path = str(COVERAGE_DIR / component / "coverage.xml")
            else:
                xml_path = str(COVERAGE_DIR / "coverage.xml")
            cmd.append(f"--cov-report=xml:{xml_path}")

        # Add fail-under option if specified
        if fail_under is not None:
            cmd.append(f"--cov-fail-under={fail_under}")

    # Run pytest
    print(f"Running: {' '.join(cmd)}")
    start_time = time.time()
    process = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    # Print the output
    print(f"\nTest execution completed in {duration:.2f} seconds")
    print(f"Return code: {process.returncode}")

    if process.stdout:
        if verbose:
            print("\nSTDOUT:")
            print(process.stdout)
        else:
            # Just print the summary lines from stdout
            summary_lines = extract_summary_lines(process.stdout)
            if summary_lines:
                print("\nTest Summary:")
                for line in summary_lines:
                    print(line)

    if process.stderr and (verbose or process.returncode != 0):
        print("\nSTDERR:")
        print(process.stderr)

    # Extract coverage percentage if coverage was enabled
    if coverage:
        coverage_percentage = extract_coverage_percentage(process.stdout)
        print(f"\nOverall coverage: {coverage_percentage:.2f}%")

    return process, coverage_percentage


def extract_summary_lines(output: str) -> list[str]:
    """Extract test summary lines from pytest output."""
    summary_lines = []
    in_summary = False

    for line in output.split("\n"):
        if "= FAILURES =" in line or "= short test summary info =" in line:
            in_summary = True
            summary_lines.append(line)
        elif in_summary and line.strip() and "====" not in line:
            summary_lines.append(line)
        elif in_summary and "====" in line:
            in_summary = False
            summary_lines.append(line)
        elif "= " in line and " =" in line and "passed" in line:
            summary_lines.append(line)

    return summary_lines


def extract_coverage_percentage(output: str) -> float:
    """Extract the coverage percentage from pytest-cov output."""
    # Look for the line containing the total coverage percentage
    # Pattern: "TOTAL                   123      45      63%"
    for line in output.split("\n"):
        if line.strip().startswith("TOTAL"):
            # Extract the percentage value
            match = re.search(r"(\d+)%$", line.strip())
            if match:
                return float(match.group(1))

    return 0.0


def extract_component_coverage(output: str, component: str | None = None) -> dict[str, float]:
    """Extract coverage percentage for each component from pytest-cov output."""
    component_coverage = {}

    if component:
        # For component-specific runs, extract module-level coverage
        module_pattern = rf"src/{component}/([\w/\.]+)\s+\d+\s+\d+\s+(\d+)%"
        for line in output.split("\n"):
            match = re.search(module_pattern, line)
            if match:
                module_name = match.group(1)
                coverage_value = float(match.group(2))
                component_coverage[f"{component}.{module_name}"] = coverage_value
    else:
        # For full runs, extract component-level coverage
        for comp in COMPONENTS:
            # Pattern: "src/component/      123      45      63%"
            comp_pattern = rf"src/{comp}/[\s-]+\d+\s+\d+\s+(\d+)%"

            for line in output.split("\n"):
                match = re.search(comp_pattern, line)
                if match:
                    component_coverage[comp] = float(match.group(1))

    return component_coverage


def generate_markdown_summary(
    component: str | None,
    process: subprocess.CompletedProcess,
    coverage_percentage: float,
    component_coverage: dict[str, float],
) -> str:
    """Generate a Markdown summary of the test results and coverage."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Start building the markdown report
    md_lines = [
        f"# Test Coverage Report - {now}",
        "",
        "## Overview",
        "",
        f"- **Component**: {component.upper() if component else 'ALL COMPONENTS'}",
        f"- **Overall Coverage**: {coverage_percentage:.2f}%",
        f"- **Test Status**: {'PASSED' if process.returncode == 0 else 'FAILED'}",
        "",
        "## Component Coverage Breakdown",
        "",
    ]

    # Add component coverage table
    md_lines.append("| Component | Coverage |")
    md_lines.append("|-----------|----------|")

    for comp, cov in sorted(component_coverage.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {comp} | {cov:.2f}% |")

    # Add test summary
    md_lines.extend(
        [
            "",
            "## Test Summary",
            "",
            "```",
            *extract_summary_lines(process.stdout),
            "```",
            "",
        ]
    )

    # Add areas for improvement
    low_coverage_threshold = 50.0  # Consider components below 50% as needing improvement
    low_coverage_components = [
        comp for comp, cov in component_coverage.items() if cov < low_coverage_threshold
    ]

    md_lines.extend(
        [
            "## Areas for Improvement",
            "",
        ]
    )

    if low_coverage_components:
        md_lines.append("The following components have low test coverage and should be improved:")
        md_lines.append("")

        for comp in low_coverage_components:
            md_lines.append(f"- **{comp}**: {component_coverage[comp]:.2f}%")
    else:
        md_lines.append(
            "All components have reasonable test coverage. Focus on maintaining and improving the test suite."
        )

    return "\n".join(md_lines)


def save_markdown_summary(component: str | None, markdown_content: str) -> Path:
    """Save the markdown summary to a file and return the file path."""
    if component:
        report_file = COVERAGE_DIR / component / "report.md"
    else:
        report_file = COVERAGE_DIR / "detailed_report.md"

    with open(report_file, "w") as f:
        f.write(markdown_content)

    return report_file


def main():
    """Main function to run comprehensive tests."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests with coverage reporting")
    parser.add_argument(
        "--component",
        choices=["backend", "embedding", "retrieval"],
        help="Component to test",
    )
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage reports")
    parser.add_argument("--xml", action="store_true", help="Generate XML coverage reports")
    parser.add_argument(
        "--fail-under",
        type=int,
        help=f"Exit with error if coverage is below specified percentage (default: {DEFAULT_COVERAGE_THRESHOLD} if coverage is enabled)",
    )

    args = parser.parse_args()

    # Set coverage flag based on args
    coverage_enabled = not args.no_coverage

    # Set fail-under threshold
    fail_under = (
        args.fail_under
        if args.fail_under is not None
        else (DEFAULT_COVERAGE_THRESHOLD if coverage_enabled else None)
    )

    # Print test information
    print("\n" + "=" * 80)
    print(" Comprehensive Test Runner ".center(80, "="))
    print("=" * 80 + "\n")

    if args.component:
        print(f"Testing component: {args.component.upper()}")
    else:
        print("Testing ALL COMPONENTS")

    print(f"Coverage reporting: {'ENABLED' if coverage_enabled else 'DISABLED'}")
    if coverage_enabled:
        print(f"HTML reports: {'ENABLED' if args.html else 'DISABLED'}")
        print(f"XML reports: {'ENABLED' if args.xml else 'DISABLED'}")
        if fail_under is not None:
            print(f"Fail if coverage is below: {fail_under}%")

    print(f"Base directory: {BASE_DIR}")
    print(f"Source directory: {SRC_DIR}")
    print(f"Tests directory: {TEST_DIR}")
    print("")

    # Ensure all necessary directories exist
    ensure_directories_exist()

    # --- BEGIN MODIFICATION: Run schema setup script ---
    print("\n" + "-" * 80)
    print(" Ensuring test database schema ".center(80, "-"))
    print("-" * 80 + "\n")

    schema_setup_cmd = [
        sys.executable,
        str(BASE_DIR / "temp_scripts" / "ensure_db_schema_for_tests.py"),
    ]
    if args.verbose:
        schema_setup_cmd.append("--verbose")

    print(f"Running schema setup: {' '.join(schema_setup_cmd)}")
    schema_process = subprocess.run(schema_setup_cmd, capture_output=True, text=True)

    if schema_process.returncode == 0:
        print("✅ Test database schema setup successful.")
    else:
        print("❌ ERROR: Test database schema setup failed!")
        print("STDOUT:")
        print(schema_process.stdout)
        print("STDERR:")
        print(schema_process.stderr)
        print("❌ Critical error: Test database schema setup failed. Exiting.")
        sys.exit(1)  # Exit if DB schema setup fails

    # --- Ensure Qdrant is ready ---
    print("\n" + "-" * 80)
    print(" Ensuring Qdrant service is ready ".center(80, "-"))
    print("-" * 80 + "\n")

    qdrant_setup_cmd = [
        sys.executable,
        str(BASE_DIR / "temp_scripts" / "ensure_qdrant_for_tests.py"),
    ]
    if args.verbose:
        qdrant_setup_cmd.append("--verbose")
    # You might want to pass --host and --port if they can differ from defaults for tests
    # qdrant_setup_cmd.extend(["--host", "localhost", "--port", "6333"]) # Example if defaults are not always used

    print(f"Running Qdrant setup: {' '.join(qdrant_setup_cmd)}")
    qdrant_process = subprocess.run(qdrant_setup_cmd, capture_output=True, text=True)

    if qdrant_process.returncode == 0:
        print("✅ Qdrant service check and setup successful.")
    else:
        print("❌ ERROR: Qdrant service check or setup failed!")
        print("STDOUT:")
        print(qdrant_process.stdout)
        print("STDERR:")
        print(qdrant_process.stderr)
        print("❌ Critical error: Qdrant service check or setup failed. Exiting.")
        sys.exit(1)  # Exit if Qdrant setup fails

    print("\n" + "-" * 80)
    print(" Starting Pytest Execution ".center(80, "-"))
    print("-" * 80 + "\n")
    # --- END MODIFICATION ---

    # Run pytest
    process, coverage_percentage = run_pytest(
        args.component, coverage_enabled, args.verbose, args.html, args.xml, fail_under
    )

    # Extract component coverage
    component_coverage = {}
    if coverage_enabled and process.stdout:
        component_coverage = extract_component_coverage(process.stdout, args.component)

    # Generate and save markdown summary
    if coverage_enabled:
        markdown_summary = generate_markdown_summary(
            args.component, process, coverage_percentage, component_coverage
        )
        report_file = save_markdown_summary(args.component, markdown_summary)
        print(f"\nDetailed report saved to: {report_file}")

    # Print final status
    print("\n" + "=" * 80)
    status = "PASSED" if process.returncode == 0 else "FAILED"
    print(f" Test Execution: {status} ".center(80, "="))
    if coverage_enabled:
        coverage_status = (
            "PASSED" if fail_under is None or coverage_percentage >= fail_under else "FAILED"
        )
        print(f" Coverage: {coverage_percentage:.2f}% - {coverage_status} ".center(80, "="))
    print("=" * 80 + "\n")

    # Return appropriate exit code
    if process.returncode != 0:
        return process.returncode
    if fail_under is not None and coverage_percentage < fail_under:
        print(
            f"Coverage {coverage_percentage:.2f}% is below the required threshold of {fail_under}%"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
