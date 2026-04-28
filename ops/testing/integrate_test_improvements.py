#!/usr/bin/env python3
"""
Test Infrastructure Integration Script

This script integrates key test improvements from temporary scripts into
the existing test infrastructure. It helps merge useful functionality while
preserving the established test framework.

Key features:
1. Imports the most useful utilities from temporary scripts
2. Integrates them with existing test infrastructure
3. Documents the changes made

Usage:
    python scripts/testing/integrate_test_improvements.py --mode [check|apply]
"""

import argparse
import os


def ensure_directory_exists(path):
    """Ensure a directory exists, creating it if necessary."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    return path


def setup_testing_directory():
    """Set up the testing directory structure."""
    # Create scripts/testing directory if it doesn't exist
    testing_dir = ensure_directory_exists("scripts/testing")

    # Create subdirectories
    ensure_directory_exists(os.path.join(testing_dir, "helpers"))
    ensure_directory_exists(os.path.join(testing_dir, "fixtures"))
    ensure_directory_exists(os.path.join(testing_dir, "mocks"))

    return testing_dir


def extract_functions_from_script(script_path, output_path, functions_to_extract):
    """Extract specific functions from a script and save them to a new file."""
    if not os.path.exists(script_path):
        print(f"Warning: Script {script_path} does not exist. Skipping.")
        return False

    with open(script_path) as f:
        content = f.read()

    # Extract imports
    import_lines = []
    for line in content.split("\n"):
        if line.startswith(("import ", "from ")):
            import_lines.append(line)

    # Build new file content
    new_content = [
        "#!/usr/bin/env python3",
        '"""',
        f"Utility functions extracted from {os.path.basename(script_path)}",
        "",
        "This module contains key functionality extracted from temporary scripts",
        "and integrated into the permanent test infrastructure.",
        '"""',
        "",
        *import_lines,
        "",
        "",
    ]

    # Extract each function
    for func_name in functions_to_extract:
        # Simple heuristic to find function definition
        func_start = content.find(f"def {func_name}")
        if func_start == -1:
            print(f"Warning: Function {func_name} not found in {script_path}")
            continue

        # Find the end of the function
        # This is a simplistic approach and might not work for all cases
        # A more robust approach would involve parsing the Python code
        lines = content[func_start:].split("\n")
        func_lines = []
        indent = None

        for line in lines:
            if not line.strip() and not func_lines:  # Skip empty lines at the beginning
                continue

            if indent is None and line.strip():
                # Determine the indentation of the function
                indent = len(line) - len(line.lstrip())
                func_lines.append(line)
            elif indent is not None:
                if line and not line.isspace() and len(line) - len(line.lstrip()) <= indent:
                    # We've reached a line with less indentation, meaning we're out of the function
                    break
                func_lines.append(line)

        new_content.extend(func_lines)
        new_content.append("")
        new_content.append("")

    # Write to output file
    with open(output_path, "w") as f:
        f.write("\n".join(new_content))

    print(f"Extracted functions from {script_path} to {output_path}")
    return True


def create_test_helpers():
    """Create test helper modules by extracting key functionality."""
    helpers_dir = "scripts/testing/helpers"

    # Extract environment setup functionality
    extract_functions_from_script(
        "temp_scripts/setup_test_environment.py",
        os.path.join(helpers_dir, "environment_setup.py"),
        ["install_required_dependencies", "setup_environment_variables", "setup_mock_database"],
    )

    # Extract import fixing functionality
    extract_functions_from_script(
        "temp_scripts/fix_test_imports.py",
        os.path.join(helpers_dir, "import_fixer.py"),
        ["fix_imports", "fix_relative_imports", "fix_parameter_mismatches"],
    )

    # Extract test execution functionality
    extract_functions_from_script(
        "temp_scripts/run_comprehensive_tests.py",
        os.path.join(helpers_dir, "test_runner.py"),
        ["run_tests_with_coverage", "generate_coverage_report", "run_component_tests"],
    )


def create_integration_script():
    """Create a script that integrates the test improvements with existing infrastructure."""
    script_path = "scripts/testing/run_improved_tests.py"

    content = """#!/usr/bin/env python3
\"\"\"
Improved Test Runner

This script enhances the existing test infrastructure with improvements
extracted from temporary test scripts. It provides a more robust way to
run tests with proper environment setup, dependency management, and
comprehensive coverage reporting.

Usage:
    python scripts/testing/run_improved_tests.py [--component COMPONENT] [--type TYPE]
\"\"\"

import argparse
import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import helper modules
from testing.helpers.environment_setup import install_required_dependencies, setup_environment_variables
from testing.helpers.import_fixer import fix_imports
from testing.helpers.test_runner import run_tests_with_coverage


def parse_args():
    \"\"\"Parse command line arguments.\"\"\"
    parser = argparse.ArgumentParser(description="Run tests with improved infrastructure")

    parser.add_argument(
        "--component",
        choices=["backend", "embedding", "retrieval", "all"],
        default="all",
        help="Component to test (default: all)"
    )

    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run (default: all)"
    )

    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip environment setup and dependency installation"
    )

    parser.add_argument(
        "--fix-imports",
        action="store_true",
        help="Fix import paths in test files before running tests"
    )

    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )

    return parser.parse_args()


def main():
    \"\"\"Main function to run tests with improved infrastructure.\"\"\"
    args = parse_args()

    if not args.skip_setup:
        print("Setting up test environment...")
        install_required_dependencies()
        setup_environment_variables()

    if args.fix_imports:
        print("Fixing import paths in test files...")
        if args.component != "all":
            fix_imports(f"tests/{args.component}")
        else:
            fix_imports("tests")

    # Run tests
    component = None if args.component == "all" else args.component
    test_type = None if args.type == "all" else args.type

    success = run_tests_with_coverage(
        component=component,
        test_type=test_type,
        html_report=args.html_report
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
"""

    with open(script_path, "w") as f:
        f.write(content)

    # Make the script executable
    os.chmod(script_path, 0o755)

    print(f"Created integration script: {script_path}")


def create_helper_init_files():
    """Create __init__.py files in helper directories."""
    dirs = [
        "scripts/testing",
        "scripts/testing/helpers",
        "scripts/testing/fixtures",
        "scripts/testing/mocks",
    ]

    for dir_path in dirs:
        init_file = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write('"""Test infrastructure module."""\n')
            print(f"Created {init_file}")


def update_readme():
    """Create or update README file for the testing infrastructure."""
    readme_path = "scripts/testing/README.md"

    content = """# Test Infrastructure

This directory contains the integrated test infrastructure for the Cyber Defense Analyst AI Assistant project.

## Overview

The test infrastructure provides tools and utilities for:

1. Setting up test environments
2. Running tests with proper dependency management
3. Generating comprehensive coverage reports
4. Fixing common test issues

## Directory Structure

- `helpers/`: Utility functions for test execution and setup
- `fixtures/`: Reusable test fixtures
- `mocks/`: Mock objects and responses for tests

## Usage

### Running Tests

```bash
# Run all tests
python scripts/testing/run_improved_tests.py

# Run tests for a specific component
python scripts/testing/run_improved_tests.py --component embedding

# Run only unit tests
python scripts/testing/run_improved_tests.py --type unit

# Generate HTML coverage report
python scripts/testing/run_improved_tests.py --html-report

# Fix import paths before running tests
python scripts/testing/run_improved_tests.py --fix-imports
```

### Environment Setup

The test infrastructure automatically sets up the required test environment, including:

1. Installing required dependencies
2. Setting environment variables
3. Creating temporary database connections

To skip environment setup:

```bash
python scripts/testing/run_improved_tests.py --skip-setup
```

## Integration with Existing Infrastructure

This infrastructure enhances the existing test framework with improvements extracted from temporary scripts, including:

1. More robust dependency management
2. Automated import path fixing
3. Comprehensive coverage reporting
4. Better test isolation and mocking

For detailed information on the test infrastructure, see `docs/test_infrastructure_guide.md`.
"""

    with open(readme_path, "w") as f:
        f.write(content)

    print(f"Created README: {readme_path}")


def perform_integration(mode="check"):
    """Perform the integration of test improvements."""
    if mode == "check":
        print("Checking integration steps (dry run)...")
        return

    print("Setting up directory structure...")
    setup_testing_directory()

    print("Creating helper modules...")
    create_test_helpers()

    print("Creating integration script...")
    create_integration_script()

    print("Creating __init__.py files...")
    create_helper_init_files()

    print("Updating README...")
    update_readme()

    print("\nIntegration complete!")
    print("The test improvements have been integrated into the existing infrastructure.")
    print("You can now use the new test runner: python scripts/testing/run_improved_tests.py")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Integrate test improvements")
    parser.add_argument(
        "--mode",
        choices=["check", "apply"],
        default="check",
        help="Mode of operation: check (dry run) or apply (make changes)",
    )

    args = parser.parse_args()
    perform_integration(args.mode)


if __name__ == "__main__":
    main()
