#!/usr/bin/env python3
"""
Verification script for tool database schema.

Tests database operations, constraints, and relationships.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import models
from src.backend.app.db.models import (
    Tool,
    ToolHealthCheck,
    ToolInvocation,
    ToolPermission,
    ToolSecret,
)


def get_database_url() -> str:
    """Get database URL from environment."""
    # Override DATABASE_URL to use localhost:5433 for testing
    return "postgresql+psycopg://testuser:test_password_123@localhost:5433/aio-test"


def test_database_connection() -> bool:
    """Test basic database connection."""
    print("🔍 Testing database connection...")

    engine = create_engine(get_database_url())

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row is None:
                raise ValueError("No result returned from database")
            assert row[0] == 1
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_tool_tables_exist() -> bool:
    """Test that all tool tables exist."""
    print("🔍 Testing tool tables exist...")

    engine = create_engine(get_database_url())

    expected_tables = [
        "tools",
        "tool_secrets",
        "tool_health_checks",
        "tool_permissions",
        "tool_invocations",
    ]

    try:
        with engine.connect() as conn:
            for table in expected_tables:
                result = conn.execute(
                    text(
                        f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = '{table}'
                    )
                """
                    )
                )
                row = result.fetchone()
                if row is None:
                    print(f"❌ No result for table '{table}'")
                    return False
                exists = row[0]
                if not exists:
                    print(f"❌ Table '{table}' does not exist")
                    return False
                print(f"✅ Table '{table}' exists")

        print("✅ All tool tables exist")
        return True
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False


def test_tool_creation() -> bool:
    """Test creating a tool in the database."""
    print("🔍 Testing tool creation...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Create a test tool
            tool = Tool(
                tool_id="test_elasticsearch",
                name="Test Elasticsearch",
                description="Test Elasticsearch tool",
                category="database",
                provider="elastic",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="http",
                mcp_endpoint="http://elasticsearch:9200",
                mcp_protocol_version="2024-11-05",
                capabilities={"tools": ["search"]},
                parameters_schema={"query": {"type": "string"}},
                requires_authentication=True,
                authentication_type="api_key",
                secret_name="elasticsearch_api_key",
                config_options={"index": "documents"},
                timeout_seconds=30,
                rate_limit_per_minute=100,
                max_concurrent_calls=5,
                is_enabled=True,
                health_check_interval_seconds=300,
                version="1.0.0",
                documentation_url="https://docs.example.com",
                tags=["search", "database"],
            )

            session.add(tool)
            session.commit()
            session.refresh(tool)

            assert tool.id is not None
            assert tool.tool_id == "test_elasticsearch"
            assert tool.name == "Test Elasticsearch"
            assert tool.category == "database"
            assert tool.tool_purpose == "retrieval"
            assert tool.service_location == "retrieval_service"
            assert tool.mcp_server_type == "http"
            assert tool.is_enabled is True
            assert tool.tags == ["search", "database"]

            print("✅ Tool creation successful")

            # Test tool retrieval
            retrieved_tool = session.query(Tool).filter_by(tool_id="test_elasticsearch").first()
            assert retrieved_tool is not None
            assert retrieved_tool.name == "Test Elasticsearch"

            print("✅ Tool retrieval successful")

            # Clean up
            session.delete(tool)
            session.commit()

            print("✅ Tool cleanup successful")
            return True

    except Exception as e:
        print(f"❌ Tool creation failed: {e}")
        return False


def test_tool_constraints() -> bool:
    """Test tool constraints and validation."""
    print("🔍 Testing tool constraints...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Test unique constraint on tool_id
            tool1 = Tool(
                tool_id="duplicate_test",
                name="First Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool1)
            session.commit()

            # Try to create second tool with same tool_id
            tool2 = Tool(
                tool_id="duplicate_test",
                name="Second Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool2)

            try:
                session.commit()
                print("❌ Unique constraint failed - duplicate tool_id allowed")
                return False
            except Exception:
                print("✅ Unique constraint working - duplicate tool_id rejected")
                session.rollback()

            # Test category constraint
            invalid_tool = Tool(
                tool_id="invalid_category_tool",
                name="Invalid Category Tool",
                category="invalid_category",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(invalid_tool)

            try:
                session.commit()
                print("❌ Category constraint failed - invalid category allowed")
                return False
            except Exception:
                print("✅ Category constraint working - invalid category rejected")
                session.rollback()

            # Clean up
            session.delete(tool1)
            session.commit()

            print("✅ Tool constraints working correctly")
            return True

    except Exception as e:
        print(f"❌ Tool constraints test failed: {e}")
        return False


def test_tool_secret_creation() -> bool:
    """Test creating a tool secret."""
    print("🔍 Testing tool secret creation...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Create a test tool first with unique ID
            import time

            tool = Tool(
                tool_id=f"secret_test_tool_{int(time.time())}",
                name="Secret Test Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool)
            session.commit()
            session.refresh(tool)

            # Create a secret for the tool
            secret = ToolSecret(
                tool_id=tool.id,
                secret_name="test_api_key",
                secret_type="api_key",
                encrypted_value=b"encrypted_data_here",
                encryption_key_id="default",
            )

            session.add(secret)
            session.commit()
            session.refresh(secret)

            assert secret.id is not None
            assert secret.tool_id == tool.id
            assert secret.secret_name == "test_api_key"
            assert secret.secret_type == "api_key"
            assert secret.encrypted_value == b"encrypted_data_here"
            assert secret.encryption_key_id == "default"
            assert secret.is_active is True
            assert secret.access_count == 0

            print("✅ Tool secret creation successful")

            # Test secret retrieval
            retrieved_secret = (
                session.query(ToolSecret).filter_by(secret_name="test_api_key").first()
            )
            assert retrieved_secret is not None
            assert retrieved_secret.tool_id == tool.id

            print("✅ Tool secret retrieval successful")

            # Clean up
            session.delete(secret)
            session.delete(tool)
            session.commit()

            print("✅ Tool secret cleanup successful")
            return True

    except Exception as e:
        print(f"❌ Tool secret creation failed: {e}")
        return False


def test_tool_health_check() -> bool:
    """Test creating a tool health check."""
    print("🔍 Testing tool health check...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Create a test tool first
            tool = Tool(
                tool_id="health_test_tool",
                name="Health Test Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool)
            session.commit()
            session.refresh(tool)

            # Create a health check
            health_check = ToolHealthCheck(
                tool_id=tool.id,
                status="online",
                response_time_ms=150.5,
                error_message=None,
                error_code=None,
                mcp_server_info={"version": "1.0.0", "capabilities": ["search"]},
            )

            session.add(health_check)
            session.commit()
            session.refresh(health_check)

            assert health_check.id is not None
            assert health_check.tool_id == tool.id
            assert health_check.status == "online"
            assert health_check.response_time_ms == 150.5
            assert health_check.error_message is None
            assert health_check.mcp_server_info == {"version": "1.0.0", "capabilities": ["search"]}

            print("✅ Tool health check creation successful")

            # Clean up
            session.delete(health_check)
            session.delete(tool)
            session.commit()

            print("✅ Tool health check cleanup successful")
            return True

    except Exception as e:
        print(f"❌ Tool health check creation failed: {e}")
        return False


def test_tool_permission() -> bool:
    """Test creating a tool permission."""
    print("🔍 Testing tool permission...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Create a test tool first
            tool = Tool(
                tool_id="permission_test_tool",
                name="Permission Test Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool)
            session.commit()
            session.refresh(tool)

            # Create a permission
            permission = ToolPermission(
                tool_id=tool.id,
                role="analyst",
                can_view=True,
                can_use=True,
                can_configure=False,
                max_calls_per_hour=100,
                max_calls_per_day=1000,
            )

            session.add(permission)
            session.commit()
            session.refresh(permission)

            assert permission.id is not None
            assert permission.tool_id == tool.id
            assert permission.role == "analyst"
            assert permission.can_view is True
            assert permission.can_use is True
            assert permission.can_configure is False
            assert permission.max_calls_per_hour == 100
            assert permission.max_calls_per_day == 1000

            print("✅ Tool permission creation successful")

            # Clean up
            session.delete(permission)
            session.delete(tool)
            session.commit()

            print("✅ Tool permission cleanup successful")
            return True

    except Exception as e:
        print(f"❌ Tool permission creation failed: {e}")
        return False


def test_tool_invocation() -> bool:
    """Test creating a tool invocation."""
    print("🔍 Testing tool invocation...")

    engine = create_engine(get_database_url())
    session_factory = sessionmaker(bind=engine)

    try:
        with session_factory() as session:
            # Create a test tool first with unique ID
            import time

            tool = Tool(
                tool_id=f"invocation_test_tool_{int(time.time())}",
                name="Invocation Test Tool",
                category="database",
                tool_purpose="retrieval",
                service_location="retrieval_service",
                mcp_server_type="stdio",
            )
            session.add(tool)
            session.commit()
            session.refresh(tool)

            # Create an invocation
            invocation = ToolInvocation(
                tool_id=tool.id,
                run_id="test_run_123",
                user_id=UUID("8137260d-9bd9-47fb-9f30-f52f32a599c6"),  # Use existing user ID
                center_id="test_center",
                tool_name="elasticsearch_search",
                tool_parameters={"query": "test query"},
                status="success",
                response_data={"hits": [], "total": 0},
                error_message=None,
                completed_at=datetime.now(UTC),
                duration_ms=150.5,
                mcp_protocol_version="2024-11-05",
                cost_estimate=0.001,
            )

            session.add(invocation)
            session.commit()
            session.refresh(invocation)

            assert invocation.id is not None
            assert invocation.tool_id == tool.id
            assert invocation.run_id == "test_run_123"
            assert invocation.tool_name == "elasticsearch_search"
            assert invocation.status == "success"
            assert invocation.duration_ms == 150.5
            assert invocation.cost_estimate == 0.001

            print("✅ Tool invocation creation successful")

            # Clean up
            session.delete(invocation)
            session.delete(tool)
            session.commit()

            print("✅ Tool invocation cleanup successful")
            return True

    except Exception as e:
        print(f"❌ Tool invocation creation failed: {e}")
        return False


def main() -> int:
    """Run all verification tests."""
    print("🚀 Starting tool database verification...")
    print("=" * 60)

    tests = [
        ("Database Connection", test_database_connection),
        ("Tool Tables Exist", test_tool_tables_exist),
        ("Tool Creation", test_tool_creation),
        ("Tool Constraints", test_tool_constraints),
        ("Tool Secret Creation", test_tool_secret_creation),
        ("Tool Health Check", test_tool_health_check),
        ("Tool Permission", test_tool_permission),
        ("Tool Invocation", test_tool_invocation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)

        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Tool database schema is working correctly.")
        return 0
    print("⚠️  Some tests failed. Please check the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
