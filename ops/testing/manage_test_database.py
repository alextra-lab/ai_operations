#!/usr/bin/env python3
"""
Test Database Management Script

This script provides comprehensive management of the test database including
setup, verification, cleanup, and status checking.

Usage:
    python scripts/testing/manage_test_database.py <command> [options]

Commands:
    setup     - Set up the test database (create, migrate, verify)
    verify    - Verify the test database is working correctly
    reset     - Reset the test database (drop, recreate, migrate)
    status    - Show current status of the test database
    cleanup   - Clean up test data (keep structure, remove data)
    drop      - Drop the test database completely
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import psycopg
from psycopg.sql import SQL, Identifier

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_db_manager")

# Test database configuration
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "testuser",
    "password": "test_password_123",
    "database": "aio-test",
    "default_db": "postgres",
    "admin_user": "Alex",  # Admin user for database operations
}


async def test_connection():
    """Test connection to PostgreSQL server."""
    try:
        # Test admin connection first
        admin_conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(admin_conninfo)
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        return False


async def database_exists():
    """Check if the test database exists."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        cursor = await conn.execute(
            SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(SQL("%s")),
            [TEST_DB_CONFIG["database"]],
        )
        row = await cursor.fetchone()
        exists = row is not None

        await conn.close()
        return exists
    except Exception as e:
        logger.error(f"❌ Error checking database existence: {e}")
        return False


async def create_database():
    """Create the test database."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(conninfo, autocommit=True)

        create_sql = SQL("CREATE DATABASE {}").format(Identifier(TEST_DB_CONFIG["database"]))
        await conn.execute(create_sql)

        await conn.close()
        logger.info(f"✅ Created database: {TEST_DB_CONFIG['database']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database: {e}")
        return False


async def drop_database():
    """Drop the test database."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['admin_user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['default_db']}"
        conn = await psycopg.AsyncConnection.connect(conninfo, autocommit=True)

        drop_sql = SQL("DROP DATABASE IF EXISTS {}").format(Identifier(TEST_DB_CONFIG["database"]))
        await conn.execute(drop_sql)

        await conn.close()
        logger.info(f"✅ Dropped database: {TEST_DB_CONFIG['database']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to drop database: {e}")
        return False


async def run_migrations():
    """Run database migrations."""
    try:
        # Set environment variables for migration runner
        os.environ["POSTGRES_USER"] = TEST_DB_CONFIG["user"]
        os.environ["POSTGRES_PASSWORD"] = TEST_DB_CONFIG["password"]
        os.environ["POSTGRES_HOST"] = TEST_DB_CONFIG["host"]
        os.environ["POSTGRES_PORT"] = str(TEST_DB_CONFIG["port"])
        os.environ["POSTGRES_DB"] = TEST_DB_CONFIG["database"]

        from scripts.migrations.runner import run_migrations as run_db_migrations

        logger.info("🔄 Running database migrations...")
        await run_db_migrations()
        logger.info("✅ Migrations completed")
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


async def verify_database():
    """Verify the test database is working correctly."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Check required tables
        required_tables = [
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

        missing_tables = []
        for table in required_tables:
            cursor = await conn.execute(
                SQL(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = {})"
                ).format(SQL("%s")),
                [table],
            )
            row = await cursor.fetchone()
            if not (row and row[0]):
                missing_tables.append(table)

        await conn.close()

        if missing_tables:
            logger.error(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        logger.info("✅ Database verification passed")
        return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


async def cleanup_data():
    """Clean up test data while keeping the structure."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Tables to clean (in dependency order)
        tables_to_clean = [
            "audit_logs",
            "usage_stats",
            "user_use_case_assignments",
            "user_roles",
            "prompt_templates",
            "use_cases",
            "encryption_keys",
            "refresh_tokens",
            "documents",
            "users",
        ]

        logger.info("🧹 Cleaning up test data...")
        for table in tables_to_clean:
            try:
                await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
                logger.info(f"  ✅ Cleaned {table}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not clean {table}: {e}")

        await conn.close()
        logger.info("✅ Data cleanup completed")
        return True

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False


async def show_status():
    """Show current status of the test database."""
    logger.info("📊 Test Database Status")
    logger.info("=" * 40)

    # Check PostgreSQL connection
    if await test_connection():
        logger.info("✅ PostgreSQL server: Connected")
    else:
        logger.info("❌ PostgreSQL server: Not accessible")
        return

    # Check database existence
    if await database_exists():
        logger.info(f"✅ Database '{TEST_DB_CONFIG['database']}': Exists")

        # Check database health
        if await verify_database():
            logger.info("✅ Database health: Good")
        else:
            logger.info("❌ Database health: Issues detected")
    else:
        logger.info(f"❌ Database '{TEST_DB_CONFIG['database']}': Not found")


async def setup_database():
    """Set up the test database from scratch."""
    logger.info("🚀 Setting up test database...")

    # Test connection
    if not await test_connection():
        return False

    # Create database if it doesn't exist
    if not await database_exists():
        if not await create_database():
            return False
    else:
        logger.info("(i) Database already exists")

    # Run migrations
    if not await run_migrations():
        return False

    # Verify setup
    if not await verify_database():
        return False

    logger.info("🎉 Test database setup completed successfully!")
    return True


async def reset_database():
    """Reset the test database (drop, recreate, migrate)."""
    logger.info("🔄 Resetting test database...")

    # Drop existing database
    if await database_exists() and not await drop_database():
        return False

    # Create new database
    if not await create_database():
        return False

    # Run migrations
    if not await run_migrations():
        return False

    # Verify setup
    if not await verify_database():
        return False

    logger.info("🎉 Test database reset completed successfully!")
    return True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage test database for AI Operations Platform")
    parser.add_argument(
        "command",
        choices=["setup", "verify", "reset", "status", "cleanup", "drop"],
        help="Command to execute",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"🔧 Executing command: {args.command}")
    logger.info(
        f"📋 Target: {TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
    )

    try:
        if args.command == "setup":
            success = await setup_database()
        elif args.command == "verify":
            success = await verify_database()
        elif args.command == "reset":
            success = await reset_database()
        elif args.command == "status":
            await show_status()
            success = True
        elif args.command == "cleanup":
            success = await cleanup_data()
        elif args.command == "drop":
            success = await drop_database()
        else:
            logger.error(f"Unknown command: {args.command}")
            success = False

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ Command failed: {e}")
        return 1


if __name__ == "__main__":
    import os

    sys.exit(asyncio.run(main()))
