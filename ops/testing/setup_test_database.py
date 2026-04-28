#!/usr/bin/env python3
"""
Test Database Setup Script for AI Operations Platform

This script sets up the test database for local development and testing.
It creates the aio-test database and applies all necessary migrations.

Usage:
    python scripts/testing/setup_test_database.py [--recreate] [--skip-migrations]
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import psycopg
from psycopg.sql import SQL, Identifier

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load test environment variables
from load_test_env import load_test_env

load_test_env()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_db_setup")


# Test database configuration (from env; load_test_env already loaded config/env/env.test)
def _test_db_config():
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", "testuser"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "database": os.environ.get("POSTGRES_DB", "aio-test"),
        "default_db": "postgres",
        "admin_user": os.environ.get(
            "POSTGRES_ADMIN_USER", os.environ.get("POSTGRES_USER", "postgres")
        ),
    }


TEST_DB_CONFIG = _test_db_config()


async def test_connection():
    """Test connection to PostgreSQL server."""
    try:
        # Test admin connection first
        admin_conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(admin_conninfo)
        await conn.close()
        logger.info("✅ Successfully connected to PostgreSQL server as admin")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        logger.error("Please ensure PostgreSQL is running on localhost:5432")
        return False


async def create_test_database(recreate=False):
    """Create the test database."""
    try:
        # Connect to default database as admin
        conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(conninfo, autocommit=True)

        test_db = TEST_DB_CONFIG["database"]

        # Check if database exists
        cursor = await conn.execute(
            SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(SQL("%s")), [test_db]
        )
        row = await cursor.fetchone()

        if row and recreate:
            logger.info(f"🗑️  Dropping existing test database: {test_db}")
            drop_sql = SQL("DROP DATABASE IF EXISTS {}").format(Identifier(test_db))
            await conn.execute(drop_sql)
            logger.info(f"✅ Test database '{test_db}' dropped")
            row = None

        if not row:
            logger.info(f"🏗️  Creating test database: {test_db}")
            create_sql = SQL("CREATE DATABASE {}").format(Identifier(test_db))
            await conn.execute(create_sql)
            logger.info(f"✅ Test database '{test_db}' created successfully")
        else:
            logger.info(f"(i) Test database '{test_db}' already exists")

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create test database: {e}")
        return False


async def run_migrations():
    """Run database migrations on the test database."""
    try:
        # Set environment variables for migration runner
        os.environ["POSTGRES_USER"] = TEST_DB_CONFIG["user"]
        os.environ["POSTGRES_PASSWORD"] = TEST_DB_CONFIG["password"]
        os.environ["POSTGRES_HOST"] = TEST_DB_CONFIG["host"]
        os.environ["POSTGRES_PORT"] = str(TEST_DB_CONFIG["port"])
        os.environ["POSTGRES_DB"] = TEST_DB_CONFIG["database"]

        # Import and run migrations
        from scripts.migrations.runner import run_migrations as run_db_migrations

        logger.info("🔄 Running database migrations...")
        await run_db_migrations()
        logger.info("✅ Database migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to run migrations: {e}")
        return False


async def verify_database_setup():
    """Verify that the test database is properly set up."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Check for key tables
        tables_to_check = [
            "users",
            "refresh_tokens",
            "documents",
            "usage_stats",
            "prompt_templates",
            "use_cases",
            "user_roles",
            "user_use_case_assignments",
            "encryption_keys",
            "audit_logs",
        ]

        logger.info("🔍 Verifying database tables...")
        for table in tables_to_check:
            cursor = await conn.execute(
                SQL(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = {})"
                ).format(SQL("%s")),
                [table],
            )
            row = await cursor.fetchone()
            table_exists = row[0] if row else False

            if table_exists:
                logger.info(f"  ✅ Table '{table}' exists")
            else:
                logger.warning(f"  ⚠️  Table '{table}' missing")

        # Check for sample data
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]
        logger.info(f"📊 Found {user_count} users in database")

        await conn.close()
        logger.info("✅ Database verification completed")
        return True

    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False


async def create_test_environment_file():
    """Create or update config/env/env.test with test database configuration."""
    try:
        env_file = project_root / "config" / "env" / "env.test"
        env_file.parent.mkdir(parents=True, exist_ok=True)

        env_content = f"""# Test environment (gitignored). Generated/updated by setup_test_database.py.
# Do not commit; credentials belong only in env files.

POSTGRES_USER={TEST_DB_CONFIG["user"]}
POSTGRES_PASSWORD={TEST_DB_CONFIG["password"]}
POSTGRES_HOST={TEST_DB_CONFIG["host"]}
POSTGRES_PORT={TEST_DB_CONFIG["port"]}
POSTGRES_DB={TEST_DB_CONFIG["database"]}

TESTING=true
DEVELOPMENT=false
LOG_LEVEL=INFO
"""

        with open(env_file, "w") as f:
            f.write(env_content)

        logger.info(f"✅ Test environment file: {env_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create test environment file: {e}")
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Set up test database for AI Operations Platform")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the test database even if it already exists",
    )
    parser.add_argument(
        "--skip-migrations", action="store_true", help="Skip running database migrations"
    )
    parser.add_argument(
        "--skip-verification", action="store_true", help="Skip database verification step"
    )
    args = parser.parse_args()

    logger.info("🚀 Starting test database setup...")
    logger.info(
        f"📋 Configuration: {TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
    )

    try:
        # Test connection
        if not await test_connection():
            return 1

        # Create test database
        if not await create_test_database(recreate=args.recreate):
            return 1

        # Run migrations
        if not args.skip_migrations and not await run_migrations():
            return 1

        # Verify setup
        if not args.skip_verification and not await verify_database_setup():
            return 1

        # Create test environment file
        if not await create_test_environment_file():
            return 1

        logger.info("🎉 Test database setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run tests: python scripts/testing/run_all_tests.py")
        logger.info(
            "2. Or run specific service tests: python scripts/testing/run_service_tests.py <service>"
        )
        logger.info("3. Test environment file: config/env/env.test")

        return 0

    except Exception as e:
        logger.error(f"❌ Test database setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
