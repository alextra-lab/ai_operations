from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.routers.orchestrator import get_current_user, jwt_validator, router
from app.schemas.response import FormattedResponse
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def fake_user():
    class User:
        user_id = "user1"
        sub = "alice"
        role = "user"

    return User()


@pytest.fixture(autouse=True)
def override_auth(app, fake_user):
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[jwt_validator.security] = lambda: MagicMock(credentials="tok")
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
def test_process_request_non_streaming(client):
    """Test non-streaming request processing."""
    # Mock UseCaseRunner.run() which is what the router actually calls
    mock_response = FormattedResponse(
        response="ok",
        sources=[],
        confidence=1.0,
        suggested_actions={},
        request_id="test-req",
    )

    with patch("app.routers.orchestrator.UseCaseRunner") as mock_runner_class:
        mock_runner = AsyncMock()
        mock_runner.run = AsyncMock(return_value=mock_response)
        mock_runner_class.return_value = mock_runner

        # Mock Orchestrator and its dependencies
        with patch("app.routers.orchestrator.Orchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_orch.config_loader.get_default_config.return_value = MagicMock()
            mock_orch.prompt_assembler = MagicMock()
            mock_orch.llm_router = MagicMock()
            mock_orch.response_formatter = MagicMock()
            mock_orch.telemetry_integration = MagicMock()
            mock_orch_class.return_value = mock_orch

            # Mock database dependencies
            with patch("app.routers.orchestrator.get_async_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__.return_value = mock_db
                mock_get_db.return_value.__aexit__.return_value = None

                with (
                    patch("app.routers.orchestrator.sync_engine"),
                    patch("app.routers.orchestrator.sessionmaker") as mock_sessionmaker,
                ):
                    mock_sync_db = MagicMock()
                    mock_sessionmaker.return_value.return_value = mock_sync_db

                    response = client.post("/api/v1/process", json={"query": "hi"})
                    assert response.status_code == 200
                    assert response.json()["response"] == "ok"


@pytest.mark.asyncio
def test_process_request_streaming(client):
    async def fake_stream(*args, **kwargs):
        yield FormattedResponse(response="chunk", sources=[], confidence=1.0, suggested_actions={})

    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = fake_stream()
        with client.stream(
            "POST", "/api/v1/process", json={"query": "hi", "stream": True}
        ) as response:
            assert response.status_code == 200
            chunks = list(response.iter_lines())
            assert any("chunk" in c for c in chunks)


@pytest.mark.asyncio
def test_process_request_error(client):
    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.side_effect = Exception("fail")
        response = client.post("/api/v1/process", json={"query": "hi"})
        assert response.status_code == 500
        assert "fail" in response.text


@pytest.mark.asyncio
def test_process_request_http_exception(client):
    from fastapi import HTTPException

    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.side_effect = HTTPException(status_code=418, detail="teapot")
        response = client.post("/api/v1/process", json={"query": "hi"})
        assert response.status_code == 418
        assert "teapot" in response.text


@pytest.mark.asyncio
def test_streaming_http_exception_handling(client):
    from fastapi import HTTPException

    async def error_stream(*args, **kwargs):
        raise HTTPException(status_code=429, detail="ratelimit")
        yield  # pragma: no cover

    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = error_stream()
        with client.stream(
            "POST", "/api/v1/process", json={"query": "hi", "stream": True}
        ) as response:
            # HTTPException in a streaming generator yields error data, not a 429 status
            assert response.status_code == 200
            chunks = list(response.iter_lines())
            assert any("ratelimit" in c for c in chunks if c)


@pytest.mark.asyncio
def test_streaming_generic_exception_handling(client):
    async def error_stream(*args, **kwargs):
        raise Exception("streamfail2")
        yield  # pragma: no cover

    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = error_stream()
        with client.stream(
            "POST", "/api/v1/process", json={"query": "hi", "stream": True}
        ) as response:
            assert response.status_code == 200
            chunks = list(response.iter_lines())
            assert any("streamfail2" in c for c in chunks if c)


@pytest.mark.asyncio
def test_streaming_error_handling(client):
    async def error_stream(*args, **kwargs):
        raise Exception("streamfail")
        yield  # pragma: no cover

    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = error_stream()
        with client.stream(
            "POST", "/api/v1/process", json={"query": "hi", "stream": True}
        ) as response:
            assert response.status_code == 200
            chunks = list(response.iter_lines())
            assert any("streamfail" in c for c in chunks if c)


@pytest.mark.asyncio
def test_process_request_missing_query(client):
    response = client.post("/api/v1/process", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
def test_process_request_null_context_and_type(client):
    with patch(
        "app.routers.orchestrator.Orchestrator.process", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = FormattedResponse(
            response="ok",
            sources=[],
            confidence=1.0,
            suggested_actions={},
            request_id="test-req",
        )
        response = client.post(
            "/api/v1/process",
            json={"query": "hi", "context": None, "request_type": None},
        )
        assert response.status_code == 200
        assert response.json()["response"] == "ok"


@pytest.mark.asyncio
def test_streaming_http_exception_on_generator_creation(client):
    from fastapi import HTTPException

    with (
        patch(
            "app.routers.orchestrator.Orchestrator.process",
            side_effect=HTTPException(status_code=418, detail="streamfailgen"),
        ),
        pytest.raises(RuntimeError, match="Caught handled exception, but response already started"),
    ):
        client.post("/api/v1/process", json={"query": "hi", "stream": True})


@pytest.mark.asyncio
def test_streaming_generic_exception_on_generator_creation(client):
    with (
        patch(
            "app.routers.orchestrator.Orchestrator.process",
            side_effect=Exception("streamfailgen2"),
        ),
        pytest.raises(Exception, match="streamfailgen2"),
    ):
        client.post("/api/v1/process", json={"query": "hi", "stream": True})
