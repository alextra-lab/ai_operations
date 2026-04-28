import inspect

from fastapi.testclient import TestClient


def test_debug_route_inspection():
    """Debug test to inspect the actual route definition"""

    from src.llm_guard_svc.app.main import app

    # Find the /api/validate route
    validate_route = None
    for route in app.routes:
        if hasattr(route, "path") and route.path == "/api/validate":
            validate_route = route
            break

    if validate_route:
        print(f"Found route: {validate_route}")
        print(f"Route path: {validate_route.path}")
        print(f"Route methods: {validate_route.methods}")

        if hasattr(validate_route, "endpoint"):
            endpoint = validate_route.endpoint
            print(f"Endpoint function: {endpoint}")
            print(f"Endpoint name: {endpoint.__name__}")

            # Get the function signature
            sig = inspect.signature(endpoint)
            print(f"Endpoint signature: {sig}")

            # Check each parameter
            for name, param in sig.parameters.items():
                print(f"  Parameter '{name}':")
                print(f"    Type: {param.annotation}")
                print(f"    Default: {param.default}")
                print(f"    Kind: {param.kind}")

        # Check if there's a dependency resolver
        if hasattr(validate_route, "dependant"):
            dependant = validate_route.dependant
            print(f"Route dependant: {dependant}")

            if hasattr(dependant, "body_params"):
                print(f"Body params: {dependant.body_params}")

            if hasattr(dependant, "query_params"):
                print(f"Query params: {dependant.query_params}")

            if hasattr(dependant, "path_params"):
                print(f"Path params: {dependant.path_params}")

            if hasattr(dependant, "header_params"):
                print(f"Header params: {dependant.header_params}")
    else:
        print("No /api/validate route found!")
        print("Available routes:")
        for route in app.routes:
            if hasattr(route, "path"):
                print(f"  {route.path}")

    assert True


def test_debug_openapi_schema_detailed():
    """Debug test to check the detailed OpenAPI schema"""

    from src.llm_guard_svc.app.main import app

    # Get the OpenAPI schema
    schema = app.openapi()

    if "/api/validate" in schema.get("paths", {}):
        validate_path = schema["paths"]["/api/validate"]
        print(f"Full /api/validate schema: {validate_path}")

        if "post" in validate_path:
            post_schema = validate_path["post"]
            print("\nPOST method schema:")

            # Check request body
            if "requestBody" in post_schema:
                request_body = post_schema["requestBody"]
                print(f"Request body: {request_body}")

                if "content" in request_body:
                    content = request_body["content"]
                    print(f"Content types: {list(content.keys())}")

                    if "application/json" in content:
                        json_schema = content["application/json"]
                        print(f"JSON schema: {json_schema}")

            # Check parameters
            if "parameters" in post_schema:
                parameters = post_schema["parameters"]
                print(f"Parameters: {parameters}")

            # Check responses
            if "responses" in post_schema:
                responses = post_schema["responses"]
                print(f"Responses: {responses}")

    assert True


def test_debug_manual_request_construction():
    """Debug test to manually construct the request that FastAPI expects"""

    from src.llm_guard_svc.app.main import app

    client = TestClient(app)

    # Try different payload structures to see what works

    # Test 1: Original structure (what we expect to work)
    payload1 = {
        "input_text": "Test input",
        "context": {"source": "test"},
        "strict_mode": False,
    }
    print(f"Test 1 - Original structure: {payload1}")
    response1 = client.post("/api/validate", json=payload1)
    print(f"Response 1: {response1.status_code} - {response1.text}")

    # Test 2: Wrapped in "request" field (what the error suggests)
    payload2 = {
        "request": {
            "input_text": "Test input",
            "context": {"source": "test"},
            "strict_mode": False,
        }
    }
    print(f"\nTest 2 - Wrapped in request: {payload2}")
    response2 = client.post("/api/validate", json=payload2)
    print(f"Response 2: {response2.status_code} - {response2.text}")

    # Test 3: Try with query parameters
    print("\nTest 3 - With query parameters")
    response3 = client.post("/api/validate?name=test", json=payload1)
    print(f"Response 3: {response3.status_code} - {response3.text}")

    # Test 4: Try form data instead of JSON
    print("\nTest 4 - Form data")
    response4 = client.post("/api/validate", data=payload1)
    print(f"Response 4: {response4.status_code} - {response4.text}")

    assert True
