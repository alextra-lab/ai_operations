import json

from fastapi.testclient import TestClient


def test_openapi_schema_detailed():
    """Check the OpenAPI schema in detail to see what FastAPI thinks the endpoint should look like"""

    from src.llm_guard_svc.app.main import app

    client = TestClient(app)

    print("=== OPENAPI SCHEMA ANALYSIS ===")
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    if "/api/validate" in schema.get("paths", {}):
        validate_path = schema["paths"]["/api/validate"]
        print("Full /api/validate path schema:")
        print(json.dumps(validate_path, indent=2))

        if "post" in validate_path:
            post_method = validate_path["post"]
            print("\nPOST method details:")
            print(f"- operationId: {post_method.get('operationId')}")
            print(f"- summary: {post_method.get('summary')}")

            # Check parameters
            if "parameters" in post_method:
                print(f"- parameters: {post_method['parameters']}")
            else:
                print("- parameters: None")

            # Check request body
            if "requestBody" in post_method:
                request_body = post_method["requestBody"]
                print(f"- requestBody required: {request_body.get('required')}")

                if "content" in request_body:
                    content = request_body["content"]
                    print(f"- content types: {list(content.keys())}")

                    if "application/json" in content:
                        json_content = content["application/json"]
                        print(f"- JSON schema: {json_content.get('schema')}")

                        # Check if the schema references ValidationRequest
                        schema_ref = json_content.get("schema", {})
                        if "$ref" in schema_ref:
                            ref_path = schema_ref["$ref"]
                            print(f"- Schema reference: {ref_path}")

                            # Try to resolve the reference
                            if (
                                ref_path.startswith("#/components/schemas/")
                                and "components" in schema
                                and "schemas" in schema["components"]
                            ):
                                schema_name = ref_path.split("/")[-1]
                                if schema_name in schema["components"]["schemas"]:
                                    resolved_schema = schema["components"]["schemas"][schema_name]
                                    print(f"- Resolved schema for {schema_name}:")
                                    print(json.dumps(resolved_schema, indent=4))
    else:
        print("ERROR: /api/validate not found in OpenAPI schema!")
        print(f"Available paths: {list(schema.get('paths', {}).keys())}")

    assert True


def test_fastapi_version_and_config():
    """Check FastAPI version and configuration"""

    import fastapi
    import pydantic

    print("=== VERSION INFORMATION ===")
    print(f"FastAPI version: {fastapi.__version__}")
    print(f"Pydantic version: {pydantic.__version__}")

    from src.llm_guard_svc.app.main import app

    print("\n=== APP CONFIGURATION ===")
    print(f"App debug: {getattr(app, 'debug', 'N/A')}")
    print(f"App title: {getattr(app, 'title', 'N/A')}")
    print(f"App version: {getattr(app, 'version', 'N/A')}")

    # Check middleware
    print("\n=== MIDDLEWARE ===")
    print(f"User middleware: {len(app.user_middleware)} items")
    for i, middleware in enumerate(app.user_middleware):
        print(f"  {i}: {middleware}")

    # Check dependency overrides
    print("\n=== DEPENDENCY OVERRIDES ===")
    print(f"Dependency overrides: {len(app.dependency_overrides)} items")
    for dep, override in app.dependency_overrides.items():
        print(f"  {dep} -> {override}")

    assert True


def test_raw_http_request():
    """Make a raw HTTP request to see exactly what FastAPI receives"""

    from src.llm_guard_svc.app.main import app

    # Create a test client that shows us the raw request/response
    with TestClient(app) as client:
        print("=== RAW HTTP REQUEST TEST ===")

        payload = {
            "input_text": "Test input",
            "context": {"source": "test"},
            "strict_mode": False,
        }

        print(f"Sending payload: {json.dumps(payload, indent=2)}")

        # Make the request and capture detailed information
        try:
            response = client.post(
                "/api/validate",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response body: {response.text}")

            # If it's a 422, parse the validation error details
            if response.status_code == 422:
                try:
                    error_detail = response.json()
                    print("\nValidation error details:")
                    for error in error_detail.get("detail", []):
                        print(f"  - Type: {error.get('type')}")
                        print(f"  - Location: {error.get('loc')}")
                        print(f"  - Message: {error.get('msg')}")
                        print(f"  - Input: {error.get('input')}")
                        print("  ---")
                except Exception:
                    print("Could not parse error details as JSON")

        except Exception as e:
            print(f"Request failed with exception: {e}")
            import traceback

            traceback.print_exc()

    assert True


def test_pydantic_model_validation():
    """Test Pydantic model validation directly"""

    from src.llm_guard_svc.app.main import ValidationRequest, ValidationResponse

    print("=== PYDANTIC MODEL VALIDATION ===")

    # Test ValidationRequest creation
    test_data = {
        "input_text": "Test input",
        "context": {"source": "test"},
        "strict_mode": False,
    }

    try:
        validation_request = ValidationRequest(**test_data)
        print("ValidationRequest created successfully:")
        print(f"  - input_text: {validation_request.input_text}")
        print(f"  - context: {validation_request.context}")
        print(f"  - strict_mode: {validation_request.strict_mode}")

        # Test serialization
        json_data = validation_request.model_dump_json()
        print(f"  - JSON serialization: {json_data}")

        # Test deserialization
        recreated = ValidationRequest.model_validate_json(json_data)
        print(f"  - Deserialization successful: {recreated == validation_request}")

    except Exception as e:
        print(f"ValidationRequest creation failed: {e}")
        import traceback

        traceback.print_exc()

    # Test ValidationResponse creation
    try:
        response_data = {
            "sanitized_text": "Test output",
            "risk_score": 0.5,
            "modified": True,
            "details": {"test": "data"},
        }

        validation_response = ValidationResponse(**response_data)
        print("\nValidationResponse created successfully:")
        print(f"  - sanitized_text: {validation_response.sanitized_text}")
        print(f"  - risk_score: {validation_response.risk_score}")
        print(f"  - modified: {validation_response.modified}")
        print(f"  - details: {validation_response.details}")

    except Exception as e:
        print(f"ValidationResponse creation failed: {e}")
        import traceback

        traceback.print_exc()

    assert True


def test_minimal_fastapi_app():
    """Create a minimal FastAPI app with the same endpoint to isolate the issue"""

    from fastapi import FastAPI, Header, Request
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field

    print("=== MINIMAL FASTAPI APP TEST ===")

    # Create minimal versions of the models
    class MinimalValidationRequest(BaseModel):
        input_text: str = Field(..., description="Text input to validate")
        context: dict[str, str] | None = Field(default=None, description="Optional context")
        strict_mode: bool = Field(False, description="Strict mode flag")

    class MinimalValidationResponse(BaseModel):
        sanitized_text: str = Field(..., description="Sanitized text")
        risk_score: float = Field(..., description="Risk score")
        modified: bool = Field(..., description="Modified flag")
        details: dict = Field(..., description="Details")

    # Create minimal app
    minimal_app = FastAPI(title="Minimal Test App")

    @minimal_app.post("/api/validate", response_model=MinimalValidationResponse)
    async def minimal_validate_input(
        request: MinimalValidationRequest,
        req: Request,
        x_user_id: str | None = Header(None),
        x_request_id: str | None = Header(None),
    ):
        return MinimalValidationResponse(
            sanitized_text=request.input_text,
            risk_score=0.0,
            modified=False,
            details={"status": "test", "message": "Minimal test successful"},
        )

    # Test the minimal app
    client = TestClient(minimal_app)

    payload = {
        "input_text": "Test input",
        "context": {"source": "test"},
        "strict_mode": False,
    }

    print(f"Testing minimal app with payload: {payload}")
    response = client.post("/api/validate", json=payload)
    print(f"Minimal app response: {response.status_code}")
    print(f"Minimal app response body: {response.text}")

    if response.status_code == 200:
        print("SUCCESS: Minimal app works correctly!")
        data = response.json()
        assert data["sanitized_text"] == "Test input"
        assert data["details"]["status"] == "test"
    else:
        print(f"FAILURE: Minimal app also fails with: {response.text}")

    assert True
