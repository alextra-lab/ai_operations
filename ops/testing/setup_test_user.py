#!/usr/bin/env python3
"""
Test User Setup Script

This script creates a dedicated test user for the AI Operations Platform (AIOP) test database
with appropriate permissions for testing.

Usage:
    python scripts/testing/setup_test_user.py [--drop-existing]
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
logger = logging.getLogger("test_user_setup")

# Test user configuration
TEST_USER_CONFIG = {
    "username": "testuser",
    "password": "test_password_123",
    "host": "localhost",
    "port": 5432,
    "database": "aio-test",
    "admin_user": "Alex",  # Your local PostgreSQL admin user
}


async def test_admin_connection():
    """Test connection as admin user."""
    try:
        conninfo = f"postgresql://{TEST_USER_CONFIG['admin_user']}@{TEST_USER_CONFIG['host']}:{TEST_USER_CONFIG['port']}/postgres"
        conn = await psycopg.AsyncConnection.connect(conninfo)
        await conn.close()
        logger.info("✅ Admin connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Admin connection failed: {e}")
        return False


async def user_exists():
    """Check if the test user already exists."""
    try:
        conninfo = f"postgresql://{TEST_USER_CONFIG['admin_user']}@{TEST_USER_CONFIG['host']}:{TEST_USER_CONFIG['port']}/postgres"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        cursor = await conn.execute(
            SQL("SELECT 1 FROM pg_roles WHERE rolname = {}").format(SQL("%s")),
            [TEST_USER_CONFIG["username"]],
        )
        row = await cursor.fetchone()
        exists = row is not None

        await conn.close()
        return exists
    except Exception as e:
        logger.error(f"❌ Error checking user existence: {e}")
        return False


async def create_test_user(drop_existing=False):
    """Create the test user with appropriate permissions."""
    try:
        conninfo = f"postgresql://{TEST_USER_CONFIG['admin_user']}@{TEST_USER_CONFIG['host']}:{TEST_USER_CONFIG['port']}/postgres"
        conn = await psycopg.AsyncConnection.connect(conninfo, autocommit=True)

        username = TEST_USER_CONFIG["username"]
        password = TEST_USER_CONFIG["password"]

        # Drop existing user if requested
        if drop_existing and await user_exists():
            logger.info(f"🗑️  Dropping existing user: {username}")
            drop_sql = SQL("DROP USER IF EXISTS {}").format(Identifier(username))
            await conn.execute(drop_sql)

        # Create user
        if not await user_exists():
            logger.info(f"👤 Creating test user: {username}")
            create_sql = f'CREATE USER "{username}" WITH PASSWORD %s'
            await conn.execute(create_sql, [password])
            logger.info(f"✅ Created user: {username}")
        else:
            logger.info(f"(i) User {username} already exists")

        # Grant permissions
        logger.info("🔐 Setting up permissions...")

        # Basic permissions
        permissions = ["CREATEDB", "CREATEROLE", "LOGIN"]

        for permission in permissions:
            grant_sql = f'ALTER USER "{username}" {permission}'
            await conn.execute(grant_sql)
            logger.info(f"  ✅ Granted {permission}")

        # Grant database-specific permissions
        db_name = TEST_USER_CONFIG["database"]

        # Connect to the test database to grant table permissions
        db_conninfo = f"postgresql://{TEST_USER_CONFIG['admin_user']}@{TEST_USER_CONFIG['host']}:{TEST_USER_CONFIG['port']}/{db_name}"
        db_conn = await psycopg.AsyncConnection.connect(db_conninfo, autocommit=True)

        # Grant schema permissions
        schema_permissions = ["USAGE ON SCHEMA public", "CREATE ON SCHEMA public"]

        for permission in schema_permissions:
            grant_sql = f'GRANT {permission} TO "{username}"'
            await db_conn.execute(grant_sql)
            logger.info(f"  ✅ Granted {permission}")

        # Grant table permissions (if tables exist)
        table_permissions = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"]

        # Get all tables in the database
        cursor = await db_conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        )
        tables = await cursor.fetchall()

        for table_row in tables:
            table_name = table_row[0]
            for permission in table_permissions:
                grant_sql = f'GRANT {permission} ON TABLE "{table_name}" TO "{username}"'
                await db_conn.execute(grant_sql)
            logger.info(f"  ✅ Granted table permissions for {table_name}")

        # Grant sequence permissions
        cursor = await db_conn.execute(
            """
            SELECT sequence_name
            FROM information_schema.sequences
            WHERE sequence_schema = 'public'
        """
        )
        sequences = await cursor.fetchall()

        for seq_row in sequences:
            seq_name = seq_row[0]
            for permission in ["SELECT", "UPDATE", "USAGE"]:
                grant_sql = f'GRANT {permission} ON SEQUENCE "{seq_name}" TO "{username}"'
                await db_conn.execute(grant_sql)
            logger.info(f"  ✅ Granted sequence permissions for {seq_name}")

        await db_conn.close()
        await conn.close()

        logger.info("✅ User setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create test user: {e}")
        return False


async def test_user_connection():
    """Test connection as the test user."""
    try:
        username = TEST_USER_CONFIG["username"]
        password = TEST_USER_CONFIG["password"]
        host = TEST_USER_CONFIG["host"]
        port = TEST_USER_CONFIG["port"]
        database = TEST_USER_CONFIG["database"]

        conninfo = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        conn = await psycopg.AsyncConnection.connect(conninfo)

        # Test basic operations
        cursor = await conn.execute("SELECT current_user, current_database()")
        row = await cursor.fetchone()
        logger.info(f"✅ Test user connection successful: {row[0]}@{row[1]}")

        # Test table access
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        table_count = (await cursor.fetchone())[0]
        logger.info(f"✅ Can access {table_count} tables")

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Test user connection failed: {e}")
        return False


async def create_test_env_file():
    """Create updated test environment file with test user credentials."""
    try:
        env_content = f"""# Test Database Configuration
# Generated by setup_test_user.py

# Database settings for testing
POSTGRES_USER={TEST_USER_CONFIG["username"]}
POSTGRES_PASSWORD={TEST_USER_CONFIG["password"]}
POSTGRES_HOST={TEST_USER_CONFIG["host"]}
POSTGRES_PORT={TEST_USER_CONFIG["port"]}
POSTGRES_DB={TEST_USER_CONFIG["database"]}

# Testing mode
TESTING=true
DEVELOPMENT=false

# Other test settings
OPENAI_API_KEY=test_key_for_testing
LOG_LEVEL=INFO
"""

        env_file = project_root / ".env.test"
        with open(env_file, "w") as f:
            f.write(env_content)

        logger.info(f"✅ Created test environment file: {env_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create test environment file: {e}")
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Set up test user for AI Operations Platform")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing test user before creating new one",
    )
    args = parser.parse_args()

    logger.info("🚀 Starting test user setup...")
    logger.info(f"📋 Test user: {TEST_USER_CONFIG['username']}")
    logger.info(f"📋 Admin user: {TEST_USER_CONFIG['admin_user']}")

    try:
        # Test admin connection
        if not await test_admin_connection():
            return 1

        # Create test user
        if not await create_test_user(drop_existing=args.drop_existing):
            return 1

        # Test user connection
        if not await test_user_connection():
            return 1

        # Create test environment file
        if not await create_test_env_file():
            return 1

        logger.info("🎉 Test user setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Set up test database: python scripts/testing/setup_test_database.py")
        logger.info("2. Run tests: python scripts/testing/run_all_tests.py")

        return 0

    except Exception as e:
        logger.error(f"❌ Test user setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
