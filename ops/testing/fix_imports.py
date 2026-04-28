#!/usr/bin/env python3
"""
Test Import Fixing Utility for Cyber Defense Analyst AI Assistant

This script fixes import issues in test files across the project:
1. Identifies test files with import issues
2. Updates import statements to use correct module paths
3. Fixes repository method signatures where needed
4. Properly configures test directories and __init__.py files

Usage:
    python fix_test_imports.py [--component COMPONENT] [--verbose] [--fix-repo-methods]

Options:
    --component COMPONENT    Fix imports only for a specific component (backend, embedding, retrieval)
    --verbose                Enable verbose output for debugging
    --dry-run                Show what would be changed without making modifications
    --fix-repo-methods       Fix repository method signatures in addition to imports
    --interactive            Ask for confirmation before applying each change
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Define base directory
BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIR = BASE_DIR / "tests"
SRC_DIR = BASE_DIR / "src"

# Common import issues and their fixes
COMMON_IMPORT_ISSUES = {
    # Relative imports -> absolute imports
    "from app.": "from src.{component}.app.",
    "from ..app.": "from src.{component}.app.",
    "from ...app.": "from src.{component}.app.",
    "import app.": "import src.{component}.app.",
    # Missing src imports
    "from backend.": "from src.backend.",
    "from embedding.": "from src.embedding.",
    "from retrieval.": "from src.retrieval.",
    "import backend.": "import src.backend.",
    "import embedding.": "import src.embedding.",
    "import retrieval.": "import src.retrieval.",
}

# Repository method signatures that need fixing
REPOSITORY_METHOD_SIGNATURES = {
    "retrieval": {
        # Document repository methods to fix
        "DocumentRepository": {
            "get_documents": "get_all",
            "get_document_type_counts": "count_by_type",
            "get_document_state_counts": "count_by_state",
            "get_document_classification_counts": "count_by_classification",
            "get_total_size": "get_total_file_size",
            "count_recent_uploads": "count_by_date_range",
            "get_average_processing_time": "get_avg_processing_time",
        },
        # Add more repositories as needed
    }
}

# Mapping of file extensions to file types for selective processing
FILE_TYPES = {
    ".py": "Python",
    ".pyx": "Cython",
    ".pxd": "Cython",
    ".pyi": "Python Interface",
}


def find_test_files(component: str | None = None) -> list[Path]:
    """Find all test files in the project."""
    test_files = []

    # Determine the directory to search
    if component:
        search_dir = TEST_DIR / component
        # Also include integration tests that might be relevant
        integration_dir = TEST_DIR / "integration"
    else:
        search_dir = TEST_DIR

    # Walk the directory and find all Python files
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.endswith(".py") and (
                file.startswith("test_") or "__test__" in file or "conftest" in file
            ):
                file_path = Path(root) / file
                test_files.append(file_path)

    # If a component was specified, also include integration tests that might import from this component
    if component and integration_dir.exists():
        for root, _, files in os.walk(integration_dir):
            for file in files:
                if file.endswith(".py") and (file.startswith("test_") or "conftest" in file):
                    file_path = Path(root) / file
                    # Check if the file contains imports from the specified component
                    with open(file_path) as f:
                        content = f.read()
                        component_imports = [
                            f"from {component}.",
                            f"import {component}.",
                            f"from src.{component}.",
                            f"import src.{component}.",
                        ]
                        if any(imp in content for imp in component_imports):
                            test_files.append(file_path)

    return test_files


def detect_component_from_path(file_path: Path) -> str | None:
    """Detect the component a file belongs to based on its path."""
    path_str = str(file_path.resolve())

    if "/backend/" in path_str or "/tests/backend/" in path_str:
        return "backend"
    if "/embedding/" in path_str or "/tests/embedding/" in path_str:
        return "embedding"
    if "/retrieval/" in path_str or "/tests/retrieval/" in path_str:
        return "retrieval"
    if "/integration/" in path_str:
        # For integration tests, try to determine from the file content
        with open(file_path) as f:
            content = f.read()
            for comp in ["backend", "embedding", "retrieval"]:
                if (
                    f"from {comp}." in content
                    or f"import {comp}." in content
                    or f"from src.{comp}." in content
                    or f"import src.{comp}." in content
                ):
                    return comp

    return None


def fix_imports_in_file(
    file_path: Path, component: str, verbose: bool, dry_run: bool, interactive: bool
) -> tuple[int, str]:
    """Fix import statements in a test file."""
    try:
        with open(file_path) as f:
            content = f.read()
    except UnicodeDecodeError:
        return 0, f"Skipping {file_path} - Binary or non-UTF-8 file"

    changes_made = 0
    change_summary = []

    # Process each common import issue
    for issue, fix in COMMON_IMPORT_ISSUES.items():
        # Replace the component placeholder with the actual component
        fix_for_component = fix.format(component=component)
        # Find all instances of the issue
        pattern = re.compile(f"^(\\s*){issue}", re.MULTILINE)
        matches = pattern.findall(content)
        match_count = len(matches)

        if match_count > 0:
            if verbose or interactive:
                print(f"Found {match_count} instances of '{issue}' in {file_path}")
                if interactive:
                    user_input = input(f"Replace with '{fix_for_component}'? (y/n): ")
                    if user_input.lower() != "y":
                        continue

            # Replace the issue with the fix
            content = pattern.sub(f"\\1{fix_for_component}", content)
            changes_made += match_count
            change_summary.append(
                f"Fixed {match_count} instances of '{issue}' -> '{fix_for_component}'"
            )

    # Write the fixed content back to the file
    if changes_made > 0 and not dry_run:
        with open(file_path, "w") as f:
            f.write(content)
        return changes_made, f"Made {changes_made} import fixes in {file_path}\n  " + "\n  ".join(
            change_summary
        )
    if changes_made > 0 and dry_run:
        return (
            changes_made,
            f"Would make {changes_made} import fixes in {file_path} (dry run)\n  "
            + "\n  ".join(change_summary),
        )
    return 0, f"No import issues found in {file_path}"


def fix_repository_methods_in_file(
    file_path: Path, component: str, verbose: bool, dry_run: bool, interactive: bool
) -> tuple[int, str]:
    """Fix repository method signatures in a test file."""
    if component not in REPOSITORY_METHOD_SIGNATURES:
        return 0, f"No repository method fixes defined for component: {component}"

    try:
        with open(file_path) as f:
            content = f.read()
    except UnicodeDecodeError:
        return 0, f"Skipping {file_path} - Binary or non-UTF-8 file"

    changes_made = 0
    change_summary = []

    # Process each repository class
    for repo_class, method_fixes in REPOSITORY_METHOD_SIGNATURES[component].items():
        # Check if this file references the repository class
        if repo_class not in content:
            continue

        # Process each method that needs fixing
        for old_method, new_method in method_fixes.items():
            # Build pattern to find method calls: repo_instance.old_method(
            # This handles various ways the instance might be named
            pattern = re.compile(r"([a-zA-Z0-9_]+)\." + re.escape(old_method) + r"\(", re.MULTILINE)

            # Find all matches
            matches = pattern.findall(content)
            match_count = len(matches)

            if match_count > 0:
                # Verify these are likely repository instances
                # This is a basic heuristic - in a real implementation we would
                # need to parse the AST to be sure
                valid_matches = []
                for instance_name in matches:
                    # Look for declarations like repo = DocumentRepository or repo: DocumentRepository
                    type_hint_pattern = re.compile(f"{instance_name}[^\\n]*:[ \\t]*{repo_class}")
                    assignment_pattern = re.compile(
                        f"{instance_name}[ \\t]*=[ \\t]*[a-zA-Z0-9_.]*{repo_class}"
                    )

                    if (
                        type_hint_pattern.search(content)
                        or assignment_pattern.search(content)
                        or
                        # Sometimes it's passed as a parameter
                        f"({repo_class}" in content
                        or
                        # Or created in-line
                        f"{instance_name} = get_{repo_class.lower()}" in content
                    ):
                        valid_matches.append(instance_name)

                if valid_matches:
                    if verbose or interactive:
                        print(
                            f"Found {len(valid_matches)} instances of '{old_method}' method in {file_path}"
                        )
                        if interactive:
                            user_input = input(f"Replace with '{new_method}'? (y/n): ")
                            if user_input.lower() != "y":
                                continue

                    # Replace each valid match
                    for instance_name in valid_matches:
                        old_call = f"{instance_name}.{old_method}("
                        new_call = f"{instance_name}.{new_method}("
                        content = content.replace(old_call, new_call)
                        changes_made += 1
                        change_summary.append(f"Fixed method call: '{old_call}' -> '{new_call}'")

    # Write the fixed content back to the file
    if changes_made > 0 and not dry_run:
        with open(file_path, "w") as f:
            f.write(content)
        return (
            changes_made,
            f"Made {changes_made} repository method fixes in {file_path}\n  "
            + "\n  ".join(change_summary),
        )
    if changes_made > 0 and dry_run:
        return (
            changes_made,
            f"Would make {changes_made} repository method fixes in {file_path} (dry run)\n  "
            + "\n  ".join(change_summary),
        )
    return 0, f"No repository method issues found in {file_path}"


def fix_test_paths_and_init_files(component: str | None, verbose: bool, dry_run: bool) -> str:
    """
    Fix test paths and ensure all test directories have __init__.py files.

    This is important for pytest to properly recognize test modules and packages.
    """
    results = []

    # Determine which directories to check
    if component:
        dirs_to_check = [(TEST_DIR / component, f"tests/{component}")]
    else:
        dirs_to_check = [
            (TEST_DIR, "tests"),
            (TEST_DIR / "backend", "tests/backend"),
            (TEST_DIR / "embedding", "tests/embedding"),
            (TEST_DIR / "retrieval", "tests/retrieval"),
            (TEST_DIR / "integration", "tests/integration"),
            (TEST_DIR / "unit", "tests/unit"),
        ]

    # Process each directory
    for dir_path, dir_name in dirs_to_check:
        if not dir_path.exists():
            if verbose:
                results.append(f"Directory {dir_name} does not exist, skipping.")
            continue

        # Create __init__.py if it doesn't exist
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            if verbose:
                results.append(f"Creating __init__.py in {dir_name}")

            if not dry_run:
                with open(init_file, "w") as f:
                    f.write(f'"""Test package for {dir_name}."""\n')

        # Check subdirectories
        for subdir in dir_path.iterdir():
            if subdir.is_dir() and not (subdir / "__init__.py").exists():
                subdir_name = f"{dir_name}/{subdir.name}"
                if verbose:
                    results.append(f"Creating __init__.py in {subdir_name}")

                if not dry_run:
                    with open(subdir / "__init__.py", "w") as f:
                        f.write(f'"""Test package for {subdir_name}."""\n')

    return "\n".join(results) if results else "All test directories have proper __init__.py files."


def analyze_import_issues(file_path: Path, _verbose: bool) -> dict[str, int]:
    """Analyze import issues in a file and return statistics."""
    try:
        with open(file_path) as f:
            content = f.read()
    except UnicodeDecodeError:
        return {"error": 1}

    issues = {}

    # Check each common import issue
    for issue in COMMON_IMPORT_ISSUES:
        # Find all instances of the issue
        pattern = re.compile(f"^(\\s*){issue}", re.MULTILINE)
        matches = pattern.findall(content)
        match_count = len(matches)

        if match_count > 0:
            issues[issue] = match_count

    return issues


def main():
    """Main function to run the import fixing utility."""
    parser = argparse.ArgumentParser(description="Fix import issues in test files")
    parser.add_argument(
        "--component",
        choices=["backend", "embedding", "retrieval"],
        help="Component to fix imports for",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making modifications",
    )
    parser.add_argument(
        "--fix-repo-methods",
        action="store_true",
        help="Fix repository method signatures in addition to imports",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ask for confirmation before applying each change",
    )

    args = parser.parse_args()

    # Print setup information
    print("\n" + "=" * 80)
    print(" Test Import Fix Utility ".center(80, "="))
    print("=" * 80 + "\n")

    if args.component:
        print(f"Fixing imports for component: {args.component.upper()}")
    else:
        print("Fixing imports for: ALL COMPONENTS")

    if args.dry_run:
        print("DRY RUN: No files will be modified")

    if args.fix_repo_methods:
        print("Also fixing repository method signatures")

    print(f"Base directory: {BASE_DIR}")
    print(f"Tests directory: {TEST_DIR}")
    print("")

    # Fix test paths and __init__.py files
    init_files_result = fix_test_paths_and_init_files(args.component, args.verbose, args.dry_run)
    if args.verbose:
        print(init_files_result)

    # Find test files
    test_files = find_test_files(args.component)
    print(f"Found {len(test_files)} test files to process.")

    # Process each test file
    total_import_fixes = 0
    total_method_fixes = 0

    for file_path in test_files:
        # Determine which component this file belongs to
        file_component = args.component or detect_component_from_path(file_path)
        if not file_component:
            if args.verbose:
                print(f"Could not determine component for {file_path}, skipping.")
            continue

        # Fix imports
        import_fixes, import_summary = fix_imports_in_file(
            file_path, file_component, args.verbose, args.dry_run, args.interactive
        )
        total_import_fixes += import_fixes

        if args.verbose or import_fixes > 0:
            print(import_summary)

        # Fix repository methods if requested
        if args.fix_repo_methods:
            method_fixes, method_summary = fix_repository_methods_in_file(
                file_path, file_component, args.verbose, args.dry_run, args.interactive
            )
            total_method_fixes += method_fixes

            if args.verbose or method_fixes > 0:
                print(method_summary)

    # Print summary
    print("\n" + "=" * 80)
    print(" Import Fix Summary ".center(80, "="))
    print("=" * 80 + "\n")

    print(f"Processed {len(test_files)} test files")
    print(f"Made {total_import_fixes} import fixes")

    if args.fix_repo_methods:
        print(f"Made {total_method_fixes} repository method fixes")

    if args.dry_run:
        print("\nThis was a dry run, no files were modified.")
        print("Run without --dry-run to apply changes.")

    # Return success
    return 0


if __name__ == "__main__":
    sys.exit(main())
