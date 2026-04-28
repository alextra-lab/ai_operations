#!/usr/bin/env python3
"""
Seed Intent Model Defaults from Environment Variables

This script migrates intent-to-model configuration from environment variables
to the database (ADR-069). Run this once during migration from env-based to
database-driven configuration.

Usage:
    python ops/database/seed_intent_defaults_from_env.py

Environment Variables Required:
    - POSTGRES_HOST
    - POSTGRES_PORT
    - POSTGRES_USER
    - POSTGRES_PASSWORD
    - POSTGRES_DB
    - INTENT_MODEL_QUERY (optional)
    - INTENT_MODEL_RULE_GENERATION (optional)
    - INTENT_MODEL_SUMMARIZATION (optional)
    - INTENT_MODEL_ENRICHMENT (optional)

The script will:
1. Read INTENT_MODEL_* environment variables
2. Validate that specified models exist in the models registry
3. Create intent_model_defaults entries for configured intents
4. Skip intents without configured env vars (will need manual configuration)
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def get_db_connection():
    """Create database connection."""
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        dbname=os.environ.get("POSTGRES_DB", "ai_operations"),
    )


def validate_model_exists(cursor, model_id: str) -> bool:
    """
    Check if a model exists in the models registry.

    Args:
        cursor: Database cursor
        model_id: Model ID to validate

    Returns:
        True if model exists and is active
    """
    cursor.execute(
        """
        SELECT COUNT(*) as count
        FROM models
        WHERE model_id = %s
        """,
        (model_id,),
    )
    result = cursor.fetchone()
    return result["count"] > 0


def check_existing_default(cursor, intent_code: str) -> bool:
    """
    Check if an active default already exists for an intent.

    Args:
        cursor: Database cursor
        intent_code: Intent code to check

    Returns:
        True if an active default exists
    """
    cursor.execute(
        """
        SELECT COUNT(*) as count
        FROM intent_model_defaults
        WHERE intent_code = %s AND is_active = TRUE
        """,
        (intent_code,),
    )
    result = cursor.fetchone()
    return result["count"] > 0


def seed_intent_default(cursor, intent_code: str, model_id: str, notes: str | None = None) -> None:
    """
    Seed an intent model default.

    Args:
        cursor: Database cursor
        intent_code: Intent code (e.g., 'QUERY')
        model_id: Model ID from registry
        notes: Optional notes about the configuration
    """
    # Check if default already exists
    if check_existing_default(cursor, intent_code):
        print(f"  ⚠️  {intent_code}: Active default already exists, skipping")
        return

    # Validate model exists
    if not validate_model_exists(cursor, model_id):
        print(f"  ❌ {intent_code}: Model '{model_id}' not found in registry, skipping")
        return

    # Insert default
    cursor.execute(
        """
        INSERT INTO intent_model_defaults (
            id, intent_code, model_id, priority, is_active,
            effective_date, notes, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, 1, TRUE,
            %s, %s, %s, %s
        )
        """,
        (
            uuid4(),
            intent_code,
            model_id,
            datetime.now(UTC),
            notes,
            datetime.now(UTC),
            datetime.now(UTC),
        ),
    )

    print(f"  ✅ {intent_code}: Configured with model '{model_id}'")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Seeding Intent Model Defaults from Environment Variables (ADR-069)")
    print("=" * 70)
    print()

    # Define intent-to-env-var mapping (only original 4 intents had env vars)
    intent_env_mapping = {
        "QUERY": "INTENT_MODEL_QUERY",
        "RULE_GENERATION": "INTENT_MODEL_RULE_GENERATION",
        "SUMMARIZATION": "INTENT_MODEL_SUMMARIZATION",
        "ENRICHMENT": "INTENT_MODEL_ENRICHMENT",
    }

    # Read environment variables
    configured_intents = {}
    for intent_code, env_var in intent_env_mapping.items():
        model_id = os.environ.get(env_var, "").strip()
        if model_id:
            configured_intents[intent_code] = model_id
            print(f"📝 Found {env_var}={model_id}")
        else:
            print(f"⚠️  {env_var} not set in environment")

    print()

    if not configured_intents:
        print("❌ No INTENT_MODEL_* environment variables found!")
        print("   Set INTENT_MODEL_QUERY, INTENT_MODEL_RULE_GENERATION, etc.")
        print("   Or configure intents manually via Admin UI after migration.")
        return 1

    print(f"Found {len(configured_intents)} configured intent(s) in environment")
    print()

    # Connect to database
    print("Connecting to database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor(row_factory=dict_row)
        print("✅ Database connection established")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return 1

    # Seed each configured intent
    print("Seeding intent model defaults:")
    print("-" * 70)

    seeded_count = 0
    for intent_code, model_id in configured_intents.items():
        try:
            seed_intent_default(
                cursor,
                intent_code,
                model_id,
                notes="Migrated from environment variable (ADR-069)",
            )
            seeded_count += 1
        except Exception as e:
            print(f"  ❌ {intent_code}: Error - {e}")
            conn.rollback()

    # Commit transaction
    conn.commit()

    print("-" * 70)
    print()

    # Summary
    print("Summary:")
    print(f"  - Configured intents: {len(configured_intents)}")
    print(f"  - Successfully seeded: {seeded_count}")
    print()

    # Check remaining intents
    cursor.execute(
        """
        SELECT it.intent_code, it.display_name
        FROM intent_types it
        LEFT JOIN intent_model_defaults imd
            ON it.intent_code = imd.intent_code
            AND imd.is_active = TRUE
        WHERE it.is_system = TRUE
          AND imd.id IS NULL
        ORDER BY it.sort_order
        """
    )
    unconfigured = cursor.fetchall()

    if unconfigured:
        print("⚠️  Intents without configured defaults:")
        for row in unconfigured:
            print(f"   - {row['intent_code']}: {row['display_name']}")
        print()
        print("   These intents will fall back to the QUERY model until configured.")
        print("   Configure them via Development UI: /dev/intent-models")
    else:
        print("✅ All system intents have configured model defaults!")

    print()
    print("Next steps:")
    print("  1. Verify configuration in Development UI (/dev/intent-models)")
    print("  2. Configure remaining intents if needed")
    print("  3. Test model selection with different intents")
    print("  4. Remove INTENT_MODEL_* env vars from .env files")
    print()

    cursor.close()
    conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
