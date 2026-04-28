import os
import sys

from fastapi.testclient import TestClient


def test_debug_import_path():
    """Debug test to see which main.py file is being imported"""

    # Print the current working directory and Python path
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")

    # Try to import and inspect the main module
    try:
        from src.llm_guard_svc.app.main import app

        print(f"Successfully imported app: {app}")
        print(f"App type: {type(app)}")

        # Check the module file path
        import src.llm_guard_svc.app.main as main_module

        print(f"Main module file: {main_module.__file__}")

        # List all attributes in the main module
        print(f"Main module attributes: {dir(main_module)}")

        # Check if ValidationRequest and ValidationResponse are available
        if hasattr(main_module, "ValidationRequest"):
            print(f"ValidationRequest found: {main_module.ValidationRequest}")
        else:
            print("ValidationRequest NOT found in main module")

        if hasattr(main_module, "ValidationResponse"):
            print(f"ValidationResponse found: {main_module.ValidationResponse}")
        else:
            print("ValidationResponse NOT found in main module")

        # Check if validate_input function exists
        if hasattr(main_module, "validate_input"):
            print(f"validate_input function found: {main_module.validate_input}")
            import inspect

            sig = inspect.signature(main_module.validate_input)
            print(f"validate_input signature: {sig}")
        else:
            print("validate_input function NOT found in main module")

    except ImportError as e:
        print(f"Import error: {e}")

    assert True


def test_debug_all_main_modules():
    """Debug test to check all main.py files in the codebase"""

    main_modules = [
        "src.llm_guard_svc.app.main",
        "src.orchestrator.app.main",
        "src.embedding.app.main",
        "src.corpus_svc.app.main",
    ]

    for module_name in main_modules:
        try:
            module = __import__(module_name, fromlist=["app"])
            print(f"\n=== {module_name} ===")
            print(f"Module file: {getattr(module, '__file__', 'Unknown')}")
            print(f"Has 'app' attribute: {hasattr(module, 'app')}")

            if hasattr(module, "app"):
                app = module.app
                print(f"App type: {type(app)}")

                # Check routes
                routes = []
                for route in app.routes:
                    if hasattr(route, "path") and hasattr(route, "methods"):
                        routes.append(f"{route.methods} {route.path}")
                print(f"Routes: {routes}")

        except ImportError as e:
            print(f"Could not import {module_name}: {e}")

    assert True


def test_debug_direct_file_import():
    """Debug test to import the specific file directly"""

    import importlib.util

    # Get the absolute path to the llm_guard_svc main.py file
    file_path = os.path.join(os.getcwd(), "src", "llm_guard_svc", "app", "main.py")
    print(f"Trying to import directly from: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")

    if os.path.exists(file_path):
        spec = importlib.util.spec_from_file_location("llm_guard_main", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        print("Direct import successful")
        print(f"Module attributes: {dir(module)}")

        if hasattr(module, "app"):
            app = module.app
            print(f"App found: {app}")

            # Test the app
            client = TestClient(app)
            response = client.get("/health")
            print(f"Health check response: {response.status_code} - {response.json()}")

            # Try the validate endpoint
            payload = {
                "input_text": "Test input",
                "context": {"source": "test"},
                "strict_mode": False,
            }
            response = client.post("/api/validate", json=payload)
            print(f"Validate response: {response.status_code} - {response.text}")

    assert True
