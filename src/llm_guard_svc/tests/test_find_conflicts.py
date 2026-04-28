import inspect
import os

from fastapi.testclient import TestClient


def test_find_all_validate_routes():
    """Find all routes that might conflict with /api/validate"""

    from src.llm_guard_svc.app.main import app

    print("=== ALL ROUTES IN THE APP ===")
    for i, route in enumerate(app.routes):
        if hasattr(route, "path"):
            print(f"{i}: {route.path} - {getattr(route, 'methods', 'N/A')}")

            # Check if this route has /api/validate
            if "/api/validate" in route.path or route.path == "/api/validate":
                print(f"  *** FOUND VALIDATE ROUTE: {route}")
                print(f"  *** Route type: {type(route)}")

                if hasattr(route, "endpoint"):
                    endpoint = route.endpoint
                    print(f"  *** Endpoint: {endpoint}")
                    if endpoint:
                        sig = inspect.signature(endpoint)
                        print(f"  *** Signature: {sig}")

                        # Check each parameter
                        for name, param in sig.parameters.items():
                            print(f"    - {name}: {param.annotation} = {param.default}")

                if hasattr(route, "dependant"):
                    dependant = route.dependant
                    print(f"  *** Dependant: {dependant}")
                    if hasattr(dependant, "query_params"):
                        print(f"  *** Query params: {dependant.query_params}")
                    if hasattr(dependant, "body_params"):
                        print(f"  *** Body params: {dependant.body_params}")

    assert True


def test_check_for_duplicate_decorators():
    """Check if there are multiple @app.post decorators in the main.py file"""

    # Read the main.py file and look for @app.post decorators
    main_file_path = "src/llm_guard_svc/app/main.py"

    if os.path.exists(main_file_path):
        with open(main_file_path) as f:
            lines = f.readlines()

        print("=== CHECKING FOR @app.post DECORATORS ===")
        for i, line in enumerate(lines, 1):
            if "@app.post" in line:
                print(f"Line {i}: {line.strip()}")
                # Print the next few lines to see the function definition
                for j in range(1, 5):
                    if i + j - 1 < len(lines):
                        print(f"Line {i+j}: {lines[i+j-1].strip()}")
                print("---")

    assert True


def test_check_imports_and_includes():
    """Check if there are any router includes that might add conflicting routes"""

    from src.llm_guard_svc.app.main import app

    print("=== CHECKING APP CONFIGURATION ===")
    print(f"App type: {type(app)}")
    print(f"App routes count: {len(app.routes)}")

    # Check if there are any included routers
    print("\n=== CHECKING FOR INCLUDED ROUTERS ===")

    # Look at the main.py file for include_router calls
    main_file_path = "src/llm_guard_svc/app/main.py"

    if os.path.exists(main_file_path):
        with open(main_file_path) as f:
            content = f.read()

        if "include_router" in content:
            print("Found include_router in main.py:")
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "include_router" in line:
                    print(f"Line {i}: {line.strip()}")
        else:
            print("No include_router found in main.py")

    assert True


def test_manual_endpoint_call():
    """Try to call the endpoint function directly to bypass FastAPI routing"""

    import asyncio
    from unittest.mock import Mock

    from fastapi import Request

    from src.llm_guard_svc.app.main import ValidationRequest, validate_input

    print("=== TESTING DIRECT FUNCTION CALL ===")

    # Create mock objects
    mock_request = Mock(spec=Request)
    mock_request.headers = {}

    # Create a ValidationRequest
    validation_request = ValidationRequest(
        input_text="Test input for direct call",
        context={"source": "direct_test"},
        strict_mode=False,
    )

    print(f"Calling validate_input directly with: {validation_request}")

    try:
        # Call the function directly with mocked dependencies
        result = asyncio.run(
            validate_input(
                request=validation_request,
                req=mock_request,
                llm_guard_instance=None,  # This should trigger the "disabled" path
                x_user_id="test-user",
                x_request_id="test-request",
            )
        )

        print("Direct call SUCCESS!")
        print(f"Result: {result}")
        print(f"Sanitized text: {result.sanitized_text}")
        print(f"Details: {result.details}")

        assert result.sanitized_text == "Test input for direct call"
        assert result.details["status"] == "disabled"

    except Exception as e:
        print(f"Direct call FAILED: {e}")
        import traceback

        traceback.print_exc()

    assert True


def test_simple_working_endpoint():
    """Test a simple endpoint that we know works to isolate the issue"""

    from src.llm_guard_svc.app.main import app

    client = TestClient(app)

    print("=== TESTING HEALTH ENDPOINT ===")
    response = client.get("/health")
    print(f"Health endpoint: {response.status_code} - {response.json()}")

    # Try to create a simple test endpoint to see if the issue is with FastAPI itself
    print("\n=== TESTING SIMPLE POST ENDPOINT ===")

    # We can't add a new endpoint here, but we can test the OpenAPI docs
    response = client.get("/docs")
    print(f"Docs endpoint: {response.status_code}")

    response = client.get("/openapi.json")
    print(f"OpenAPI endpoint: {response.status_code}")

    if response.status_code == 200:
        openapi_data = response.json()
        if "/api/validate" in openapi_data.get("paths", {}):
            validate_spec = openapi_data["paths"]["/api/validate"]
            print(f"OpenAPI spec for /api/validate: {validate_spec}")

    assert True
