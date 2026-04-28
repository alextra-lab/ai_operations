#!/usr/bin/env python3
"""
Test Database Verification Script

This script verifies that the test database is properly set up and accessible.
It checks for required tables, sample data, and connectivity.

Usage:
    python scripts/testing/verify_test_database.py
"""

import asyncio
import logging
import sys
from pathlib import Path

import psycopg
from psycopg.sql import SQL

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_db_verification")

# Test database configuration
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "Alex",
    "password": "",
    "database": "aio-test",
}


async def test_connection():
    """Test basic connection to the test database."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)
        await conn.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def check_tables():
    """Check that all required tables exist."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Required tables
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

        logger.info("🔍 Checking required tables...")
        missing_tables = []

        for table in required_tables:
            cursor = await conn.execute(
                SQL(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = {})"
                ).format(SQL("%s")),
                [table],
            )
            row = await cursor.fetchone()
            table_exists = row[0] if row else False

            if table_exists:
                logger.info(f"  ✅ {table}")
            else:
                logger.error(f"  ❌ {table} - MISSING")
                missing_tables.append(table)

        await conn.close()

        if missing_tables:
            logger.error(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        logger.info("✅ All required tables present")
        return True

    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False


async def check_sample_data():
    """Check for sample data in the database."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        logger.info("📊 Checking sample data...")

        # Check users table
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]
        logger.info(f"  👥 Users: {user_count}")

        # Check documents table
        cursor = await conn.execute("SELECT COUNT(*) FROM documents")
        doc_count = (await cursor.fetchone())[0]
        logger.info(f"  📄 Documents: {doc_count}")

        # Check use_cases table
        cursor = await conn.execute("SELECT COUNT(*) FROM use_cases")
        use_case_count = (await cursor.fetchone())[0]
        logger.info(f"  🎯 Use cases: {use_case_count}")

        # Check prompt_templates table
        cursor = await conn.execute("SELECT COUNT(*) FROM prompt_templates")
        template_count = (await cursor.fetchone())[0]
        logger.info(f"  📝 Prompt templates: {template_count}")

        await conn.close()

        if user_count > 0:
            logger.info("✅ Sample data found")
            return True
        logger.warning("⚠️  No sample data found - this may be expected for a fresh setup")
        return True

    except Exception as e:
        logger.error(f"❌ Error checking sample data: {e}")
        return False


async def check_database_permissions():
    """Check database permissions for the test user."""
    try:
        conninfo = f"postgresql://{TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        logger.info("🔐 Checking database permissions...")

        # Test basic operations
        test_operations = [
            ("SELECT", "SELECT 1"),
            (
                "INSERT",
                "INSERT INTO users (username, hashed_password, role) VALUES ('test_user', 'test_hash', 'user') ON CONFLICT DO NOTHING",
            ),
            ("UPDATE", "UPDATE users SET updated_at = NOW() WHERE username = 'test_user'"),
            ("DELETE", "DELETE FROM users WHERE username = 'test_user'"),
        ]

        for op_name, query in test_operations:
            try:
                await conn.execute(query)
                logger.info(f"  ✅ {op_name} permission")
            except Exception as e:
                logger.error(f"  ❌ {op_name} permission failed: {e}")
                return False

        await conn.close()
        logger.info("✅ All database permissions working")
        return True

    except Exception as e:
        logger.error(f"❌ Error checking permissions: {e}")
        return False


async def main():
    """Main verification function."""
    logger.info("🚀 Starting test database verification...")
    logger.info(
        f"📋 Target: {TEST_DB_CONFIG['user']}@{TEST_DB_CONFIG['host']}:{TEST_DB_CONFIG['port']}/{TEST_DB_CONFIG['database']}"
    )

    checks = [
        ("Connection", test_connection),
        ("Tables", check_tables),
        ("Sample Data", check_sample_data),
        ("Permissions", check_database_permissions),
    ]

    all_passed = True

    for check_name, check_func in checks:
        logger.info(f"\n🔍 Running {check_name} check...")
        try:
            result = await check_func()
            if not result:
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            all_passed = False

    logger.info("\n" + "=" * 50)
    if all_passed:
        logger.info("🎉 All checks passed! Test database is ready for use.")
        logger.info("\nNext steps:")
        logger.info("1. Run tests: python scripts/testing/run_all_tests.py")
        logger.info(
            "2. Or run specific tests: python scripts/testing/run_service_tests.py <service>"
        )
        return 0
    logger.error("❌ Some checks failed. Please review the errors above.")
    logger.error("\nTo fix issues:")
    logger.error("1. Run setup: python scripts/testing/setup_test_database.py --recreate")
    logger.error("2. Check PostgreSQL is running: brew services list | grep postgresql")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
