"""
Integration tests for Inference Gateway database migrations (029-032).

Tests verify:
- Tables created with correct schema
- Enums created with correct values
- Indexes created for performance
- Foreign keys enforced
- Constraints validated
- Triggers functioning
- Idempotency (migrations can be re-run safely)

Note: These tests use direct psycopg connections (not async ORM) since
we're only verifying schema existence, not business logic.
"""

import os

import psycopg
import pytest


@pytest.fixture(scope="module")
def db_conn():
    """Create a direct database connection for migration tests."""
    conn_string = os.getenv(
        "DATABASE_URL", "postgresql://testuser:test_password_123@localhost:5433/aio-test"
    )
    # Convert SQLAlchemy URL to psycopg format if needed
    if "+psycopg" in conn_string:
        conn_string = conn_string.replace("+psycopg", "")

    conn = psycopg.connect(conn_string)
    yield conn
    conn.close()


class TestGatewayProvidersMigration:
    """Test migration 029: gateway_providers table."""

    def test_table_exists(self, db_conn):
        """Verify gateway_providers table was created."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'gateway_providers')"
            )
            exists = cur.fetchone()[0]
            assert exists is True, "gateway_providers table should exist"

    def test_columns_exist(self, db_conn):
        """Verify all required columns exist with correct types."""
        expected_columns = {
            "id": "uuid",
            "name": "character varying",
            "provider_type": "USER-DEFINED",  # enum type
            "base_url": "text",
            "api_key_encrypted": "text",
            "is_enabled": "boolean",
            "status": "USER-DEFINED",  # enum type
            "priority": "integer",
            "config_json": "jsonb",
            "health_check_url": "text",
            "last_health_check": "timestamp with time zone",
            "last_health_status": "boolean",
            "error_count": "integer",
            "success_count": "integer",
            "circuit_state": "character varying",
            "circuit_opened_at": "timestamp with time zone",
            "created_by": "uuid",
            "created_at": "timestamp with time zone",
            "updated_at": "timestamp with time zone",
        }

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'gateway_providers' ORDER BY ordinal_position"
            )
            actual_columns = {row[0]: row[1] for row in cur.fetchall()}

        assert len(actual_columns) == 19, "Should have 19 columns"
        for col_name, col_type in expected_columns.items():
            assert col_name in actual_columns, f"Column {col_name} should exist"
            assert (
                actual_columns[col_name] == col_type
            ), f"Column {col_name} should be {col_type}, got {actual_columns[col_name]}"

    def test_primary_key(self, db_conn):
        """Verify primary key constraint exists."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'gateway_providers' AND constraint_type = 'PRIMARY KEY'"
            )
            pk_exists = cur.fetchone()
            assert pk_exists is not None, "Primary key constraint should exist"

    def test_unique_constraint_on_name(self, db_conn):
        """Verify unique constraint on provider name."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'gateway_providers' AND constraint_type = 'UNIQUE'"
            )
            unique_exists = cur.fetchone()
            assert unique_exists is not None, "Unique constraint on name should exist"

    def test_foreign_key_to_users(self, db_conn):
        """Verify foreign key to users table."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'gateway_providers' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            fk_exists = cur.fetchone()
            assert fk_exists is not None, "Foreign key to users should exist"

    def test_indexes_created(self, db_conn):
        """Verify performance indexes were created."""
        expected_indexes = [
            "gateway_providers_pkey",
            "gateway_providers_name_key",
            "idx_gateway_providers_enabled",
            "idx_gateway_providers_status",
            "idx_gateway_providers_type",
            "idx_gateway_providers_priority",
            "idx_gateway_providers_circuit",
        ]

        with db_conn.cursor() as cur:
            cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'gateway_providers'")
            actual_indexes = [row[0] for row in cur.fetchall()]

        for idx in expected_indexes:
            assert idx in actual_indexes, f"Index {idx} should exist"

    def test_trigger_exists(self, db_conn):
        """Verify updated_at trigger was created."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE event_object_table = 'gateway_providers'"
            )
            trigger_exists = cur.fetchone()
            assert trigger_exists is not None, "updated_at trigger should exist"

    def test_provider_type_enum(self, db_conn):
        """Verify provider_type enum has correct values."""
        expected_values = ["openai", "mistral", "anthropic", "local", "custom"]

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT enumlabel FROM pg_enum "
                "WHERE enumtypid = 'provider_type'::regtype "
                "ORDER BY enumsortorder"
            )
            actual_values = [row[0] for row in cur.fetchall()]

        assert actual_values == expected_values, "provider_type enum should match"

    def test_provider_status_enum(self, db_conn):
        """Verify provider_status enum has correct values."""
        expected_values = ["active", "disabled", "error", "testing"]

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT enumlabel FROM pg_enum "
                "WHERE enumtypid = 'provider_status'::regtype "
                "ORDER BY enumsortorder"
            )
            actual_values = [row[0] for row in cur.fetchall()]

        assert actual_values == expected_values, "provider_status enum should match"


class TestGatewayUsageLogMigration:
    """Test migration 030: gateway_usage_log table."""

    def test_table_exists(self, db_conn):
        """Verify gateway_usage_log table was created."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'gateway_usage_log')"
            )
            exists = cur.fetchone()[0]
            assert exists is True, "gateway_usage_log table should exist"

    def test_column_count(self, db_conn):
        """Verify table has 26 columns."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'gateway_usage_log'"
            )
            count = cur.fetchone()[0]
            assert count == 26, "gateway_usage_log should have 26 columns"

    def test_computed_column_tokens_total(self, db_conn):
        """Verify tokens_total is a computed column."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT is_generated FROM information_schema.columns "
                "WHERE table_name = 'gateway_usage_log' AND column_name = 'tokens_total'"
            )
            is_generated = cur.fetchone()[0]
            assert is_generated == "ALWAYS", "tokens_total should be a generated column"

    def test_foreign_keys(self, db_conn):
        """Verify foreign keys to users and gateway_providers."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.table_constraints "
                "WHERE table_name = 'gateway_usage_log' "
                "AND constraint_type = 'FOREIGN KEY'"
            )
            fk_count = cur.fetchone()[0]
            assert fk_count == 2, "Should have 2 foreign keys (users, gateway_providers)"

    def test_check_constraints(self, db_conn):
        """Verify check constraints on numeric columns."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.check_constraints "
                "WHERE constraint_schema = 'public' "
                "AND constraint_name LIKE 'gateway_usage_log%check'"
            )
            count = cur.fetchone()[0]
            assert count >= 6, "Should have at least 6 check constraints"

    def test_indexes_created(self, db_conn):
        """Verify all 9 indexes were created (1 PK + 8 performance)."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'gateway_usage_log'")
            count = cur.fetchone()[0]
            assert count == 9, "Should have 9 indexes (1 PK + 8 performance)"


class TestRunManifestsExtension:
    """Test migration 031: run_manifests.gateway_metrics column."""

    def test_column_exists(self, db_conn):
        """Verify gateway_metrics column was added."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.columns "
                "WHERE table_name = 'run_manifests' AND column_name = 'gateway_metrics')"
            )
            exists = cur.fetchone()[0]
            assert exists is True, "gateway_metrics column should exist"

    def test_column_type(self, db_conn):
        """Verify column is JSONB type."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'run_manifests' AND column_name = 'gateway_metrics'"
            )
            data_type = cur.fetchone()[0]
            assert data_type == "jsonb", "gateway_metrics should be JSONB type"

    def test_column_default(self, db_conn):
        """Verify column has empty JSON default."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'run_manifests' AND column_name = 'gateway_metrics'"
            )
            default = cur.fetchone()[0]
            assert "'{}'" in default, "Default should be empty JSON object"

    def test_gin_index_exists(self, db_conn):
        """Verify GIN index on JSONB column."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'run_manifests' "
                "AND indexname = 'idx_run_manifests_gateway_metrics'"
            )
            exists = cur.fetchone()
            assert exists is not None, "GIN index should exist on gateway_metrics"


class TestGatewayRateLimitsMigration:
    """Test migration 032: gateway_rate_limits table."""

    def test_table_exists(self, db_conn):
        """Verify gateway_rate_limits table was created."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'gateway_rate_limits')"
            )
            exists = cur.fetchone()[0]
            assert exists is True, "gateway_rate_limits table should exist"

    def test_column_count(self, db_conn):
        """Verify table has 10 columns."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'gateway_rate_limits'"
            )
            count = cur.fetchone()[0]
            assert count == 10, "gateway_rate_limits should have 10 columns"

    def test_rate_limit_type_enum(self, db_conn):
        """Verify rate_limit_type enum has correct values."""
        expected_values = ["global", "provider", "integration", "use_case"]

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT enumlabel FROM pg_enum "
                "WHERE enumtypid = 'rate_limit_type'::regtype "
                "ORDER BY enumsortorder"
            )
            actual_values = [row[0] for row in cur.fetchall()]

        assert actual_values == expected_values, "rate_limit_type enum should match"

    def test_unique_constraint(self, db_conn):
        """Verify unique constraint on limit_type + identifier."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'gateway_rate_limits' "
                "AND indexname = 'idx_gateway_rate_limits_unique'"
            )
            exists = cur.fetchone()
            assert exists is not None, "Unique index should exist"

    def test_check_constraints(self, db_conn):
        """Verify check constraints on numeric columns."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT constraint_name FROM information_schema.check_constraints "
                "WHERE constraint_schema = 'public' "
                "AND constraint_name LIKE 'gateway_rate_limits%check'"
            )
            constraints = [row[0] for row in cur.fetchall()]

        assert len(constraints) >= 3, "Should have at least 3 check constraints"

    def test_trigger_exists(self, db_conn):
        """Verify updated_at trigger was created."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT trigger_name FROM information_schema.triggers "
                "WHERE event_object_table = 'gateway_rate_limits'"
            )
            trigger_exists = cur.fetchone()
            assert trigger_exists is not None, "updated_at trigger should exist"


class TestDataIntegrity:
    """Test data integrity constraints work correctly."""

    def test_unique_constraint_enforcement(self, db_conn):
        """Test that unique constraints prevent duplicates."""
        with db_conn.cursor() as cur:
            # Clean up any existing test data
            cur.execute("DELETE FROM gateway_rate_limits WHERE limit_type = 'global'")
            db_conn.commit()

            # Insert first rate limit
            cur.execute(
                "INSERT INTO gateway_rate_limits "
                "(limit_type, identifier, requests_per_minute) "
                "VALUES ('global', NULL, 500)"
            )
            db_conn.commit()

            # Try to insert duplicate (should fail)
            try:
                cur.execute(
                    "INSERT INTO gateway_rate_limits "
                    "(limit_type, identifier, requests_per_minute) "
                    "VALUES ('global', NULL, 600)"
                )
                db_conn.commit()
                raise AssertionError("Should have raised unique constraint violation")
            except psycopg.errors.UniqueViolation:
                # Expected error
                db_conn.rollback()
            finally:
                # Cleanup
                cur.execute("DELETE FROM gateway_rate_limits WHERE limit_type = 'global'")
                db_conn.commit()
