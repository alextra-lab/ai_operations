from fastapi import FastAPI, Header, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


def test_completely_isolated_app():
    """Create a completely isolated FastAPI app to test if the issue is with the app configuration"""

    # Create a fresh FastAPI app
    isolated_app = FastAPI(title="Isolated Test App")

    # Define the models exactly as in your main app
    class IsolatedValidationRequest(BaseModel):
        input_text: str = Field(..., description="Text input to validate and sanitize")
        context: dict[str, str] | None = Field(
            default=None, description="Optional context for validation"
        )
        strict_mode: bool = Field(False, description="Whether to apply stricter validation rules")

    class IsolatedValidationResponse(BaseModel):
        sanitized_text: str = Field(..., description="Sanitized output text")
        risk_score: float = Field(..., description="Risk score (0-1, higher is riskier)")
        modified: bool = Field(..., description="Whether the input was modified")
        details: dict = Field(..., description="Detailed scanner results")

    # Define the endpoint exactly as in your main app
    @isolated_app.post("/api/validate", response_model=IsolatedValidationResponse)
    async def isolated_validate_input(
        request: IsolatedValidationRequest,
        req: Request,
        x_user_id: str | None = Header(None),
        x_request_id: str | None = Header(None),
    ):
        return IsolatedValidationResponse(
            sanitized_text=request.input_text,
            risk_score=0.0,
            modified=False,
            details={"status": "isolated_test", "message": "Isolated test successful"},
        )

    # Test the isolated app
    client = TestClient(isolated_app)

    payload = {
        "input_text": "This is a test input for isolated app.",
        "context": {"source": "isolated_test"},
        "strict_mode": False,
    }

    print(f"Testing isolated app with payload: {payload}")
    response = client.post("/api/validate", json=payload)
    print(f"Isolated app response status: {response.status_code}")
    print(f"Isolated app response body: {response.text}")

    if response.status_code == 200:
        print("SUCCESS: Isolated app works! The issue is with your main app configuration.")
        data = response.json()
        assert data["sanitized_text"] == payload["input_text"]
        assert data["details"]["status"] == "isolated_test"
    else:
        print("FAILURE: Even isolated app fails. This suggests a deeper FastAPI issue.")
        print(f"Error details: {response.text}")

    assert response.status_code == 200


def test_check_main_app_routes():
    """Check what routes are actually registered in your main app"""

    from src.llm_guard_svc.app.main import app

    print("=== MAIN APP ROUTES ===")
    for i, route in enumerate(app.routes):
        if hasattr(route, "path"):
            print(f"{i}: {route.path} - {getattr(route, 'methods', 'N/A')}")

            if route.path == "/api/validate":
                print("  *** VALIDATE ROUTE DETAILS ***")
                print(f"  Route: {route}")
                print(f"  Type: {type(route)}")

                if hasattr(route, "endpoint"):
                    endpoint = route.endpoint
                    print(f"  Endpoint function: {endpoint}")
                    print(f"  Endpoint name: {endpoint.__name__}")
                    print(f"  Endpoint module: {endpoint.__module__}")

                    import inspect

                    sig = inspect.signature(endpoint)
                    print(f"  Signature: {sig}")

                    # Check the source file
                    try:
                        source_file = inspect.getfile(endpoint)
                        print(f"  Source file: {source_file}")
                    except Exception:
                        print("  Source file: Could not determine")

    assert True


def test_check_for_duplicate_imports():
    """Check if there are multiple imports of the same module that might cause conflicts"""

    import sys

    print("=== MODULE IMPORT CHECK ===")

    # Check if there are multiple versions of the main module loaded
    main_modules = [name for name in sys.modules if "llm_guard_svc" in name and "main" in name]
    print(f"LLM Guard main modules in sys.modules: {main_modules}")

    for module_name in main_modules:
        module = sys.modules[module_name]
        print(f"  {module_name}: {getattr(module, '__file__', 'No file')}")

    # Check if there are multiple FastAPI apps
    fastapi_apps = []
    for name, module in sys.modules.items():
        if hasattr(module, "app") and "FastAPI" in str(type(getattr(module, "app", None))):
            fastapi_apps.append((name, module))

    print(f"\nFastAPI apps found: {len(fastapi_apps)}")
    for name, module in fastapi_apps:
        app_instance = module.app
        print(f"  {name}: {app_instance} (routes: {len(app_instance.routes)})")

    assert True


def test_restart_python_process():
    """Test to see if restarting helps - this will show if it's a caching issue"""

    print("=== PYTHON PROCESS RESTART TEST ===")
    print("If this test passes but the main test still fails after running this,")
    print("it suggests there's a module caching or import order issue.")
    print("Try restarting your Python process/container and running the test again.")

    # Try to clear any cached modules
    import sys

    modules_to_clear = [name for name in sys.modules if "llm_guard_svc" in name]
    print(f"Clearing cached modules: {modules_to_clear}")

    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]

    # Now try to import fresh
    try:
        from src.llm_guard_svc.app.main import app as fresh_app

        print(f"Fresh import successful: {fresh_app}")

        client = TestClient(fresh_app)
        payload = {
            "input_text": "Fresh import test",
            "context": {"source": "fresh_test"},
            "strict_mode": False,
        }

        response = client.post("/api/validate", json=payload)
        print(f"Fresh app response: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Fresh import failed: {e}")
        import traceback

        traceback.print_exc()

    assert True
