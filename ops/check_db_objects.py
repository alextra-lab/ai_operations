#!/usr/bin/env python3
"""
Check database objects in the PostgreSQL database.

This script inspects the tables, columns, indexes, sequences, and other
database objects to provide an inventory of what exists in the database.
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
logger = logging.getLogger("db_inventory")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def get_connection(db_name=None):
    """Get a PostgreSQL connection."""
    import psycopg

    # Get connection parameters from environment variables
    pg_user = os.environ.get("POSTGRES_USER", "user")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "password")
    pg_host = os.environ.get("POSTGRES_HOST", "postgres-db")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    pg_db = db_name or os.environ.get("POSTGRES_DB", "aio")

    # Log which database we're connecting to
    logger.info(f"Connecting to database: {pg_db} on {pg_host}:{pg_port}")

    # Create connection string
    conninfo = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    # Create connection
    return await psycopg.AsyncConnection.connect(conninfo)


async def check_tables(conn):
    """Check what tables exist in the public schema."""
    logger.info("Checking tables in public schema...")

    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public';
    """

    result = await conn.execute(query)
    rows = await result.fetchall()

    if rows:
        logger.info("Tables found:")
        for row in rows:
            table_name = row[0]
            logger.info(f"  - {table_name}")

            # For each table, also get column information
            await check_table_columns(conn, table_name)
    else:
        logger.info("No tables found in public schema.")

    return [row[0] for row in rows]


async def check_table_columns(conn, table_name):
    """Check the columns for a specific table."""
    query = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position;
    """

    result = await conn.execute(query, [table_name])
    rows = await result.fetchall()

    if rows:
        logger.info(f"    Columns for {table_name}:")
        for row in rows:
            column_name, data_type, is_nullable = row
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            logger.info(f"      - {column_name} ({data_type}, {nullable})")


async def check_indexes(conn):
    """Check what indexes exist in the public schema."""
    logger.info("Checking indexes in public schema...")

    query = """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    ORDER BY tablename, indexname;
    """

    result = await conn.execute(query)
    rows = await result.fetchall()

    if rows:
        logger.info("Indexes found:")
        for row in rows:
            table_name, index_name, index_def = row
            logger.info(f"  - {table_name}.{index_name}: {index_def}")
    else:
        logger.info("No indexes found in public schema.")


async def check_sequences(conn):
    """Check what sequences exist in the public schema."""
    logger.info("Checking sequences in public schema...")

    query = """
    SELECT sequence_name
    FROM information_schema.sequences
    WHERE sequence_schema = 'public';
    """

    result = await conn.execute(query)
    rows = await result.fetchall()

    if rows:
        logger.info("Sequences found:")
        for row in rows:
            logger.info(f"  - {row[0]}")
    else:
        logger.info("No sequences found in public schema.")


async def check_migration_records(conn):
    """Check what migration records exist."""
    logger.info("Checking migration records...")

    # First check if the schema_migrations table exists
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'schema_migrations'
    );
    """

    result = await conn.execute(query)
    row = await result.fetchone()

    if not row or not row[0]:
        logger.info("The schema_migrations table does not exist.")
        return

    # Query migration records
    query = "SELECT version, name, applied_at, checksum FROM schema_migrations ORDER BY version;"
    result = await conn.execute(query)
    rows = await result.fetchall()

    if rows:
        logger.info("Applied migrations:")
        for row in rows:
            version, name, applied_at, checksum = row
            logger.info(f"  - {version}: {name} (Applied: {applied_at}, Checksum: {checksum})")
    else:
        logger.info("No migration records found in schema_migrations table.")


async def check_all_objects(db_name=None):
    """Check all database objects."""
    conn = None
    try:
        conn = await get_connection(db_name)

        # Check tables and their columns
        tables = await check_tables(conn)

        # Check indexes
        await check_indexes(conn)

        # Check sequences
        await check_sequences(conn)

        # Check migration records if the table exists
        if "schema_migrations" in tables:
            await check_migration_records(conn)

        logger.info("Database inventory completed successfully.")
    except Exception as e:
        logger.error(f"Error checking database objects: {e!s}")
    finally:
        if conn and not conn.closed:
            await conn.close()
            logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check database objects")
    parser.add_argument(
        "--db-name", help="Database name to check (default: from POSTGRES_DB env var)"
    )
    args = parser.parse_args()

    asyncio.run(check_all_objects(args.db_name))


if __name__ == "__main__":
    main()
