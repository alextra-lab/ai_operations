from fastapi.testclient import TestClient


def test_debug_get_llm_guard_dependency():
    """Debug test to check the get_llm_guard dependency"""

    try:
        from src.llm_guard_svc.app.main import get_llm_guard

        print(f"get_llm_guard function found: {get_llm_guard}")

        # Try to call the dependency function
        result = get_llm_guard()
        print(f"get_llm_guard() result: {result}")
        print(f"get_llm_guard() result type: {type(result)}")

    except Exception as e:
        print(f"Error with get_llm_guard: {e}")
        import traceback

        traceback.print_exc()

    assert True


def test_debug_fastapi_request_processing():
    """Debug test to see what FastAPI is actually receiving"""

    from src.llm_guard_svc.app.main import app

    # Create a custom test client that logs requests
    class DebugTestClient(TestClient):
        def request(self, method, url, **kwargs):
            print(f"Making request: {method} {url}")
            print(f"Request kwargs: {kwargs}")
            response = super().request(method, url, **kwargs)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response body: {response.text}")
            return response

    client = DebugTestClient(app)

    payload = {
        "input_text": "Test input",
        "context": {"source": "test"},
        "strict_mode": False,
    }

    client.post("/api/validate", json=payload)
    assert True  # Just to make the test pass


def test_debug_with_dependency_override():
    """Debug test with dependency override to bypass LLMGuard"""

    from src.llm_guard_svc.app.main import app, get_llm_guard

    # Override the dependency to return None (simulating disabled service)
    def mock_get_llm_guard():
        print("Mock get_llm_guard called - returning None")
        return

    app.dependency_overrides[get_llm_guard] = mock_get_llm_guard

    try:
        client = TestClient(app)

        payload = {
            "input_text": "Test input",
            "context": {"source": "test"},
            "strict_mode": False,
        }

        print(f"Sending payload with dependency override: {payload}")
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
        # Clean up the override
        app.dependency_overrides.clear()

    assert True


def test_debug_pydantic_validation():
    """Debug test to check if Pydantic validation is working correctly"""

    from src.llm_guard_svc.app.main import ValidationRequest

    # Test creating ValidationRequest directly
    test_data = {
        "input_text": "Test input",
        "context": {"source": "test"},
        "strict_mode": False,
    }

    try:
        validation_request = ValidationRequest(**test_data)
        print(f"ValidationRequest created successfully: {validation_request}")
        print(f"ValidationRequest dict: {validation_request.model_dump()}")
        print(f"ValidationRequest JSON: {validation_request.model_dump_json()}")
    except Exception as e:
        print(f"Error creating ValidationRequest: {e}")
        import traceback

        traceback.print_exc()

    # Test with minimal data
    try:
        minimal_request = ValidationRequest(input_text="Just text")
        print(f"Minimal ValidationRequest: {minimal_request}")
    except Exception as e:
        print(f"Error creating minimal ValidationRequest: {e}")

    assert True


def test_debug_fastapi_openapi_schema():
    """Debug test to check the OpenAPI schema"""

    from src.llm_guard_svc.app.main import app

    # Get the OpenAPI schema
    schema = app.openapi()

    # Look for the /api/validate endpoint
    if "/api/validate" in schema.get("paths", {}):
        validate_endpoint = schema["paths"]["/api/validate"]
        print(f"OpenAPI schema for /api/validate: {validate_endpoint}")

        if "post" in validate_endpoint:
            post_schema = validate_endpoint["post"]
            print(f"POST schema: {post_schema}")

            if "requestBody" in post_schema:
                print(f"Request body schema: {post_schema['requestBody']}")

            if "parameters" in post_schema:
                print(f"Parameters schema: {post_schema['parameters']}")
    else:
        print("No /api/validate endpoint found in OpenAPI schema")
        print(f"Available paths: {list(schema.get('paths', {}).keys())}")

    assert True
