from fastapi.testclient import TestClient

from src.llm_guard_svc.app.main import app

client = TestClient(app)


def test_validate_input_basic():
    """Test basic validation with the correct ValidationRequest structure"""
    payload = {
        "input_text": "This is a test input for LLM-Guard.",
        "context": {"source": "test"},
        "strict_mode": False,
    }

    response = client.post("/api/validate", json=payload)

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()

    # Verify response structure matches ValidationResponse
    assert "sanitized_text" in data
    assert "risk_score" in data
    assert "modified" in data
    assert "details" in data

    # Since LLM Guard is disabled, verify the expected response
    # assert data["sanitized_text"] == payload["input_text"]
    # assert data["risk_score"] == 0.0
    # assert data["modified"] == False
    # assert data["details"]["status"] == "disabled"


def test_validate_input_minimal():
    """Test with only required field (input_text)"""
    payload = {"input_text": "Simple test input."}

    response = client.post("/api/validate", json=payload)
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()

    assert data["sanitized_text"] == payload["input_text"]
    assert data["details"]["status"] == "disabled"


def test_validate_input_with_headers():
    """Test with optional headers"""
    payload = {
        "input_text": "Test input with headers.",
        "context": {"source": "test_with_headers"},
    }

    headers = {"x-user-id": "test-user-123", "x-request-id": "test-request-456"}

    response = client.post("/api/validate", json=payload, headers=headers)
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()

    assert data["sanitized_text"] == payload["input_text"]
    assert data["details"]["status"] == "disabled"


def test_validate_input_missing_required_field():
    """Test that missing input_text returns 422"""
    payload = {"context": {"source": "test"}, "strict_mode": False}

    response = client.post("/api/validate", json=payload)
    assert response.status_code == 422
    error_detail = response.json()
    assert "detail" in error_detail
    # Check that the error mentions missing "input_text" field
    assert any("input_text" in str(detail) for detail in error_detail["detail"])


def test_health_endpoint():
    """Test the health endpoint to ensure the app is working"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "llm-guard-svc"
