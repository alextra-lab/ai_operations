#!/usr/bin/env python3
"""
Quick fix to add get_db_pool and close_db_pool functions to the connection.py file
for backward compatibility with test imports.
"""

import argparse
from pathlib import Path


def fix_connection_file():
    """
    Add get_db_pool and close_db_pool functions to connection.py that call
    the corresponding methods on DatabaseConnection.
    """
    connection_file = Path("/workspace/src/retrieval/app/db/connection.py")

    if not connection_file.exists():
        print(f"Error: {connection_file} does not exist")
        return False

    # Read the current content
    content = connection_file.read_text()

    # Check if functions already exist
    if "async def get_db_pool()" in content and "async def close_db_pool()" in content:
        print("Functions already exist, no changes needed")
        return True

    # Add the functions at the end of the file
    functions_to_add = '''

# Compatibility functions for tests
async def get_db_pool() -> Pool:
    """
    Get database connection pool.
    Compatibility function that calls DatabaseConnection.get_pool().

    Returns:
        asyncpg.Pool: Database connection pool
    """
    return await DatabaseConnection.get_pool()

async def close_db_pool() -> None:
    """
    Close database connection pool.
    Compatibility function that calls DatabaseConnection.close_pool().

    Returns:
        None
    """
    await DatabaseConnection.close_pool()
'''

    # Write the updated content
    connection_file.write_text(content + functions_to_add)
    print(f"Updated {connection_file}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Fix connection file for tests")
    parser.parse_args()

    if fix_connection_file():
        print("Connection file fixed successfully")
    else:
        print("Failed to fix connection file")
        exit(1)


if __name__ == "__main__":
    main()
