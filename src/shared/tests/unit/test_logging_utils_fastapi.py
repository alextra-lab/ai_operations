import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.logging_utils.fastapi import RequestIDLoggerMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(RequestIDLoggerMiddleware)

    @app.get("/ping")
    async def ping():
        return {"msg": "pong"}

    return app


def test_request_id_middleware_sets_header(app):
    client = TestClient(app)
    # No X-Request-ID header
    response = client.get("/ping")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    assert len(req_id) > 0

    # With X-Request-ID header
    custom_id = "test-req-id-123"
    response2 = client.get("/ping", headers={"X-Request-ID": custom_id})
    assert response2.status_code == 200
    assert response2.headers["X-Request-ID"] == custom_id
