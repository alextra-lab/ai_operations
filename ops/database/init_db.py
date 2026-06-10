#!/usr/bin/env python3
"""db-init entrypoint — runs inside the db-init container.

Applies: schema init -> seeds -> migrations -> intent defaults.

Pure-Python replacement for the former init_entrypoint.sh + psql pair, so the
image needs no OS packages (psycopg executes the .sql files directly). SQL
files are sent whole over the simple query protocol (psycopg uses it for
parameterless execute()), which allows multiple statements per file and
honors the explicit BEGIN/COMMIT blocks the files contain — matching
``psql -v ON_ERROR_STOP=1 -f`` behavior: execution stops at the first error.

The host-side runner (run_migrations.sh) remains for operators with psql;
this module replicates its logic for the container path. Keep the two in
sync if migration semantics change.
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: {name} must be set", file=sys.stderr)
        sys.exit(1)
    return value


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=require_env("POSTGRES_HOST"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=require_env("POSTGRES_USER"),
        password=require_env("POSTGRES_PASSWORD"),
        dbname=require_env("POSTGRES_DB"),
        autocommit=True,
    )


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    conn.execute(path.read_text())


def scalar(conn: psycopg.Connection, query: str, params: tuple = ()) -> object:
    row = conn.execute(query, params).fetchone()
    return row[0] if row else None


def run_migrations(conn: psycopg.Connection) -> None:
    """Replicates run_migrations.sh: apply migrations/*.sql (top level only) in order."""
    print(f"Migrations directory: {MIGRATIONS_DIR}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          name VARCHAR(255) PRIMARY KEY,
          applied_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );
        """
    )
    applied = 0
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        name = f.name
        if scalar(conn, "SELECT 1 FROM schema_migrations WHERE name = %s LIMIT 1", (name,)):
            print(f"Skip (already applied): {name}")
        else:
            print(f"Applying: {name}")
            run_sql_file(conn, f)
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (name,))
            applied += 1
    print(f"Done. Applied {applied} new migration(s).")


def seed_intent_defaults() -> None:
    """Phase 4 — non-fatal: no INTENT_MODEL_* vars = warn only."""
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "seed_intent_defaults_from_env.py")],
        check=False,
    )
    if result.returncode != 0:
        print(
            "  Note: INTENT_MODEL_* env vars not set — intent routing uses defaults"
            " from DB; configure via Admin UI"
        )


def main() -> None:
    conn = connect()

    already_init = scalar(
        conn,
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations' LIMIT 1",
    )
    if already_init == 1:
        print("=== db-init: DB already initialized — running migrations only ===")
        run_migrations(conn)
        print("=== db-init: Complete (resume) ===")
        return

    print("=== db-init: Phase 1 — Schema init (000_complete_init.sql) ===")
    run_sql_file(conn, BASE_DIR / "init" / "000_complete_init.sql")

    # Seeds run BEFORE migrations: several migrations (e.g. 036) insert data
    # that references seeded rows (intent_categories).
    print("=== db-init: Phase 2 — Seeds ===")
    for f in sorted(BASE_DIR.glob("seed/0[0-9][0-9]_*.sql")):
        print(f"  Seeding: {f.name}")
        run_sql_file(conn, f)

    print("=== db-init: Phase 3 — Migrations ===")
    run_migrations(conn)

    print("=== db-init: Phase 4 — Intent defaults ===")
    seed_intent_defaults()

    print("=== db-init: Complete ===")


if __name__ == "__main__":
    main()
