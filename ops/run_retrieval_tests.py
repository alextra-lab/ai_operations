#!/usr/bin/env python3
"""
Run integration tests for the retrieval service database components.

This script sets up the test environment and runs the tests for
the retrieval service database components, including models and repositories.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("retrieval_tests")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_test_environment():
    """Set up the test environment variables."""
    # Set testing mode
    os.environ["TESTING"] = "1"

    # Set PostgreSQL environment variables for testing
    os.environ["POSTGRES_USER"] = "testuser"
    os.environ["POSTGRES_PASSWORD"] = "test_password_123"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "aio-test"

    logger.info("Test environment configured")


async def create_test_database(recreate=False):
    """Create the test database if it doesn't exist or recreate it if requested."""
    import psycopg
    from psycopg.sql import SQL, Identifier

    # Use the default database to connect
    pg_user = os.environ.get("POSTGRES_USER", "user")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "password")
    pg_host = os.environ.get("POSTGRES_HOST", "postgres-db")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    test_db = os.environ.get("POSTGRES_DB", "aio-test")

    # Connect to the default 'postgres' database to create our test database
    default_conninfo = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/postgres"

    check_conn = None
    create_conn = None
    try:
        # Connect to the default database to check if test db exists
        logger.info(f"Connecting to PostgreSQL at {pg_host}:{pg_port}")
        check_conn = await psycopg.AsyncConnection.connect(default_conninfo)

        # Check if the test database exists
        cursor = await check_conn.execute(
            SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(SQL("%s")), [test_db]
        )
        row = await cursor.fetchone()

        # If database exists and we want to recreate it, drop it first
        if row and recreate:
            logger.info(f"Dropping existing test database: {test_db}")

            # Close first connection before creating another with autocommit
            if check_conn and not check_conn.closed:
                await check_conn.close()
                check_conn = None

            # Create a new connection with autocommit set to True
            create_conn = await psycopg.AsyncConnection.connect(default_conninfo, autocommit=True)

            # Drop the database - using SQL to properly quote the database name
            drop_sql = SQL("DROP DATABASE IF EXISTS {}").format(Identifier(test_db))
            await create_conn.execute(drop_sql)
            logger.info(f"Test database '{test_db}' dropped successfully")

            # Set row to None to indicate database doesn't exist anymore
            row = None

        if not row:
            # Database doesn't exist, create it
            logger.info(f"Creating test database: {test_db}")

            # Close first connection before creating another with autocommit if not already done
            if check_conn and not check_conn.closed:
                await check_conn.close()
                check_conn = None

            # Create a new connection with autocommit if not already created
            if not create_conn or create_conn.closed:
                create_conn = await psycopg.AsyncConnection.connect(
                    default_conninfo, autocommit=True
                )

            # Create the database - using SQL to properly quote the database name
            create_sql = SQL("CREATE DATABASE {}").format(Identifier(test_db))
            await create_conn.execute(create_sql)
            logger.info(f"Test database '{test_db}' created successfully")
        else:
            logger.info(f"Test database '{test_db}' already exists")

        # Success
        return True
    except Exception as e:
        logger.error(f"Failed to create/recreate test database: {e!s}")
        logger.error(
            "Please ensure PostgreSQL is running and you have permission to create databases.\n"
            "You can manually create the test database with:\n"
            f"  CREATE DATABASE {test_db};"
        )
        return False
    finally:
        # Make sure to close all connections
        if check_conn and not check_conn.closed:
            await check_conn.close()
        if create_conn and not create_conn.closed:
            await create_conn.close()


async def verify_tables_exist():
    """Verify that the tables were properly created in the test database."""
    import psycopg

    # Get connection parameters from environment
    pg_user = os.environ.get("POSTGRES_USER", "user")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "password")
    pg_host = os.environ.get("POSTGRES_HOST", "postgres-db")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    test_db = os.environ.get("POSTGRES_DB", "aio-test")

    # Create connection string for the test database
    conninfo = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{test_db}"

    conn = None
    try:
        # Connect directly to the test database
        logger.info(f"Verifying tables in database: {test_db}")
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Check if required tables exist
        tables_to_check = ["schema_migrations", "documents", "chunks", "access_stats"]
        for table in tables_to_check:
            query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
            """
            result = await conn.execute(query, [table])
            row = await result.fetchone()
            table_exists = row[0] if row else False

            if table_exists:
                logger.info(f"Table '{table}' exists in database")
            else:
                logger.error(f"Table '{table}' does NOT exist in database!")

                # If a table doesn't exist, check if there was an error creating it
                logger.info(f"Checking for error messages while creating '{table}'")
                # Check schema_migrations table for entries
                if table != "schema_migrations":
                    try:
                        migrations_query = "SELECT * FROM schema_migrations ORDER BY version;"
                        migrations_result = await conn.execute(migrations_query)
                        migrations_rows = await migrations_result.fetchall()
                        logger.info(f"Applied migrations: {migrations_rows}")
                    except Exception as e:
                        logger.error(f"Could not query schema_migrations: {e!s}")

        return True
    except Exception as e:
        logger.error(f"Error verifying tables: {e!s}")
        return False
    finally:
        if conn and not conn.closed:
            await conn.close()


async def run_migrations():
    """Run database migrations to set up test database schema."""
    # type: ignore[import-not-found]
    from scripts.migrations.runner import run_migrations as run_db_migrations

    logger.info("Running database migrations for test database...")
    await run_db_migrations()
    logger.info("Database migrations completed")


async def run_tests(pattern=None):
    """
    Run the tests using pytest.

    Args:
        pattern: Optional test pattern to run specific tests
    """
    import subprocess
    import sys

    # Build pytest arguments - use subprocess to avoid event loop conflicts
    args = [sys.executable, "-m", "pytest", "-xvs"]

    # Add asyncio mode to avoid event loop conflicts
    args.append("--asyncio-mode=auto")

    # Add test pattern if provided
    if pattern:
        args.append(pattern)
    else:
        args.append("tests/retrieval")

    logger.info(f"Running tests with args: {args}")

    # Run pytest as a separate process to avoid event loop conflicts
    result = subprocess.run(args, check=False)

    return result.returncode


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run retrieval tests")
    parser.add_argument(
        "--pattern",
        help=(
            "Test pattern to run specific tests "
            "(e.g. 'tests/retrieval/integration/test_document_repository.py')"
        ),
    )
    parser.add_argument(
        "--skip-migrations", action="store_true", help="Skip running migrations before tests"
    )
    parser.add_argument(
        "--skip-db-creation", action="store_true", help="Skip creating the test database"
    )
    parser.add_argument(
        "--recreate-db",
        action="store_true",
        help="Recreate the test database even if it already exists",
    )
    args = parser.parse_args()

    try:
        # Setup test environment
        setup_test_environment()

        # Create test database if not skipped
        if not args.skip_db_creation:
            db_created = await create_test_database(recreate=args.recreate_db)
            if not db_created:
                return 1

        # Run migrations if not skipped
        if not args.skip_migrations:
            await run_migrations()

            # Verify tables were created
            await verify_tables_exist()

        # Run tests
        return await run_tests(args.pattern)
    except Exception as e:
        logger.error(f"Error running tests: {e!s}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
