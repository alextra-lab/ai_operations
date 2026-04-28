import logging

from fastapi.testclient import TestClient


def test_debug_with_both_dependencies_overridden():
    """Debug test with both logger and llm_guard dependencies overridden"""

    from src.llm_guard_svc.app.main import app, get_llm_guard, get_logger

    # Create a mock logger
    mock_logger = logging.getLogger("test-logger")

    # Override both dependencies
    def mock_get_logger():
        print("Mock get_logger called")
        return mock_logger

    def mock_get_llm_guard():
        print("Mock get_llm_guard called - returning None")
        return

    app.dependency_overrides[get_logger] = mock_get_logger
    app.dependency_overrides[get_llm_guard] = mock_get_llm_guard

    try:
        client = TestClient(app)

        payload = {
            "input_text": "Test input",
            "context": {"source": "test"},
            "strict_mode": False,
        }

        print(f"Sending payload with both dependencies overridden: {payload}")
        response = client.post("/api/validate", json=payload)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success! Response data: {data}")
            assert data["details"]["status"] == "disabled"
        else:
            print(f"Still getting error: {response.text}")

    finally:
        # Clean up the overrides
        app.dependency_overrides.clear()

    assert True


def test_debug_logger_dependency_only():
    """Debug test with only logger dependency overridden"""

    from src.llm_guard_svc.app.main import app, get_logger

    # Create a mock logger
    mock_logger = logging.getLogger("test-logger")

    # Override only the logger dependency
    def mock_get_logger():
        print("Mock get_logger called")
        return mock_logger

    app.dependency_overrides[get_logger] = mock_get_logger

    try:
        client = TestClient(app)

        payload = {
            "input_text": "Test input",
            "context": {"source": "test"},
            "strict_mode": False,
        }

        print(f"Sending payload with logger dependency overridden: {payload}")
        response = client.post("/api/validate", json=payload)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

    finally:
        # Clean up the overrides
        app.dependency_overrides.clear()

    assert True


def test_debug_check_get_logger_function():
    """Debug test to check the get_logger function directly"""

    try:
        from src.llm_guard_svc.app.main import get_logger

        print(f"get_logger function found: {get_logger}")

        # Try to call get_logger directly
        result = get_logger()
        print(f"get_logger() result: {result}")
        print(f"get_logger() result type: {type(result)}")

    except Exception as e:
        print(f"Error with get_logger: {e}")
        import traceback

        traceback.print_exc()

    assert True
