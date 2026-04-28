from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.routers.corpus import get_current_user, router
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
    return {"sub": "alice", "id": "user1"}


@pytest.fixture(autouse=True)
def override_get_current_user(app, fake_user):
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
def test_upload_document(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=202, json=MagicMock(return_value={"ok": True}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        files = {"file": ("test.txt", b"hello", "text/plain")}
        response = client.post("/api/v1/documents/", files=files)
        assert response.status_code == 202
        assert response.json()["ok"] is True


@pytest.mark.asyncio
def test_upload_document_with_collection(client):
    """Test uploading document to specific collection."""
    mock_instance = MagicMock()
    mock_post = AsyncMock(
        return_value=MagicMock(
            status_code=202,
            json=MagicMock(return_value={"ok": True, "collection": "threats"}),
        )
    )
    mock_instance.__aenter__.return_value.post = mock_post
    with patch("httpx.AsyncClient", return_value=mock_instance):
        files = {"file": ("test.txt", b"hello", "text/plain")}
        data = {"collection_name": "threats"}
        response = client.post("/api/v1/documents/", files=files, data=data)
        assert response.status_code == 202
        assert response.json()["ok"] is True
        # Verify collection_name was passed in the request
        _, called_kwargs = mock_post.call_args
        assert "collection_name" in called_kwargs["data"]
        assert called_kwargs["data"]["collection_name"] == "threats"


@pytest.mark.asyncio
def test_list_documents(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=[{"id": 1}]))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/")
        assert response.status_code == 200
        # Response is wrapped in {"documents": [...]}
        assert response.json()["documents"][0]["id"] == 1


@pytest.mark.asyncio
def test_get_document_statistics(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"stats": 1}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/stats")
        assert response.status_code == 200
        assert response.json()["stats"] == 1


@pytest.mark.asyncio
def test_get_document(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"id": "doc1"}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc1")
        assert response.status_code == 200
        assert response.json()["id"] == "doc1"


@pytest.mark.asyncio
def test_update_document(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.patch = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"updated": True}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.patch("/api/v1/documents/doc1", json={"title": "new"})
        assert response.status_code == 200
        assert response.json()["updated"] is True


@pytest.mark.asyncio
def test_delete_document(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.delete = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"deleted": True}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.delete("/api/v1/documents/doc1")
        assert response.status_code == 200
        assert response.json()["deleted"] is True


@pytest.mark.asyncio
def test_upload_document_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=400, text="fail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        files = {"file": ("test.txt", b"hello", "text/plain")}
        response = client.post("/api/v1/documents/", files=files)
        assert response.status_code == 400
        assert "fail" in response.text


@pytest.mark.asyncio
def test_list_documents_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="listfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/")
        assert response.status_code == 400
        assert "listfail" in response.text


@pytest.mark.asyncio
def test_get_document_statistics_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="statsfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/stats")
        assert response.status_code == 400
        assert "statsfail" in response.text


@pytest.mark.asyncio
def test_get_document_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="getfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc1")
        assert response.status_code == 400
        assert "getfail" in response.text


@pytest.mark.asyncio
def test_update_document_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.patch = AsyncMock(
        return_value=MagicMock(status_code=400, text="patchfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.patch("/api/v1/documents/doc1", json={"title": "new"})
        assert response.status_code == 400
        assert "patchfail" in response.text


@pytest.mark.asyncio
def test_delete_document_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.delete = AsyncMock(
        return_value=MagicMock(status_code=400, text="deletefail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.delete("/api/v1/documents/doc1")
        assert response.status_code == 400
        assert "deletefail" in response.text


@pytest.mark.asyncio
def test_get_document_status_error(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=400, text="statusfail")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc1/status")
        assert response.status_code == 400
        assert "statusfail" in response.text


def test_get_forward_headers():
    from typing import ClassVar

    from app.routers import corpus as corpus_mod

    class DummyRequest:
        headers: ClassVar[dict[str, str]] = {"authorization": "Bearer test"}

    assert corpus_mod.get_forward_headers(DummyRequest()) == {"authorization": "Bearer test"}

    class DummyRequest2:
        headers: ClassVar[dict[str, str]] = {}

    assert corpus_mod.get_forward_headers(DummyRequest2()) == {}


def test_get_user_id():
    from app.routers import corpus as corpus_mod

    # dict with id
    assert corpus_mod.get_user_id({"id": 1}) == "1"
    # dict with sub
    assert corpus_mod.get_user_id({"sub": "bob"}) == "bob"

    # object with id
    class U:
        id = 2

    assert corpus_mod.get_user_id(U()) == "2"

    # object with sub
    class U2:
        sub = "carol"

    assert corpus_mod.get_user_id(U2()) == "carol"
    # neither
    assert corpus_mod.get_user_id({}) is None

    class U3:
        pass

    assert corpus_mod.get_user_id(U3()) is None


@pytest.mark.asyncio
def test_get_document_no_user_id(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"id": "doc1"}))
    )
    with (
        patch("app.routers.corpus.get_current_user", return_value={}),
        patch("httpx.AsyncClient", return_value=mock_instance),
    ):
        response = client.get("/api/v1/documents/doc1")
        assert response.status_code == 200
        assert response.json()["id"] == "doc1"


@pytest.mark.asyncio
def test_get_document_status_no_user_id(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"status": "ok"}))
    )
    with (
        patch("app.routers.corpus.get_current_user", return_value={}),
        patch("httpx.AsyncClient", return_value=mock_instance),
    ):
        response = client.get("/api/v1/documents/doc1/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
def test_get_document_with_user_id():
    from app.routers.corpus import get_current_user, router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "user42"}

    mock_instance = MagicMock()
    mock_get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"id": "doc1"}))
    )
    mock_instance.__aenter__.return_value.get = mock_get
    with patch("httpx.AsyncClient", return_value=mock_instance), TestClient(app) as client:
        response = client.get("/api/v1/documents/doc1")
        assert response.status_code == 200
        assert response.json()["id"] == "doc1"
        _, called_kwargs = mock_get.call_args
        assert called_kwargs["params"]["user_id"] == "user42"


@pytest.mark.asyncio
def test_get_document_status_with_user_id():
    from app.routers.corpus import get_current_user, router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "user99"}

    mock_instance = MagicMock()
    mock_get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"status": "ok"}))
    )
    mock_instance.__aenter__.return_value.get = mock_get
    with patch("httpx.AsyncClient", return_value=mock_instance), TestClient(app) as client:
        response = client.get("/api/v1/documents/doc123/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        _, called_kwargs = mock_get.call_args
        assert called_kwargs["params"]["user_id"] == "user99"


@pytest.mark.asyncio
def test_get_document_status_success(client):
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value={"status": "ok"}))
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc999/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ============================================================================
# Tests: Download Document Endpoint
# ============================================================================


@pytest.mark.asyncio
def test_download_document_success(client):
    """Test successful document download."""
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"file content here"
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="test.pdf"',
    }
    mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc123/download")
        assert response.status_code == 200
        assert response.content == b"file content here"
        assert response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
def test_download_document_error(client):
    """Test document download error."""
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.get = AsyncMock(
        return_value=MagicMock(status_code=404, text="Document not found")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/doc123/download")
        assert response.status_code == 404
        assert "Document not found" in response.text


@pytest.mark.asyncio
def test_download_document_with_user_id():
    """Test download passes user_id to corpus service."""
    from app.routers.corpus import get_current_user, router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "user123"}

    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"content"
    mock_response.headers = {"content-type": "application/octet-stream"}
    mock_get = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__.return_value.get = mock_get

    with patch("httpx.AsyncClient", return_value=mock_instance), TestClient(app) as client:
        response = client.get("/api/v1/documents/doc456/download")
        assert response.status_code == 200
        _, called_kwargs = mock_get.call_args
        assert called_kwargs["params"]["user_id"] == "user123"


# ============================================================================
# Tests: Reprocess Document Endpoint
# ============================================================================


@pytest.mark.asyncio
def test_reprocess_document_success(client):
    """Test successful document reprocessing."""
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={"message": "Reprocessing started", "document_id": "doc123"}
            ),
        )
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/documents/doc123/reprocess")
        assert response.status_code == 200
        assert response.json()["message"] == "Reprocessing started"


@pytest.mark.asyncio
def test_reprocess_document_with_embedding_model(client):
    """Test reprocessing with specific embedding model."""
    mock_instance = MagicMock()
    mock_post = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"message": "Reprocessing started"}),
        )
    )
    mock_instance.__aenter__.return_value.post = mock_post

    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post(
            "/api/v1/documents/doc123/reprocess?embedding_model=text-embedding-3-small"
        )
        assert response.status_code == 200
        _, called_kwargs = mock_post.call_args
        assert called_kwargs["params"]["embedding_model"] == "text-embedding-3-small"


@pytest.mark.asyncio
def test_reprocess_document_error(client):
    """Test document reprocessing error."""
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=404, text="Document not found")
    )
    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.post("/api/v1/documents/doc999/reprocess")
        assert response.status_code == 404
        assert "Document not found" in response.text


# ============================================================================
# Tests: List Documents with Filters
# ============================================================================


@pytest.mark.asyncio
def test_list_documents_with_filters(client):
    """Test listing documents with query filters."""
    mock_instance = MagicMock()
    mock_get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=[{"id": "doc1"}]))
    )
    mock_instance.__aenter__.return_value.get = mock_get

    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get(
            "/api/v1/documents/?limit=20&offset=10&document_type=pdf&tag=security"
        )
        assert response.status_code == 200
        _, called_kwargs = mock_get.call_args
        params = called_kwargs["params"]
        assert params["limit"] == 20
        assert params["offset"] == 10
        assert params["type"] == "pdf"
        assert params["tag"] == "security"


@pytest.mark.asyncio
def test_list_documents_with_search_query(client):
    """Test listing documents with search query."""
    mock_instance = MagicMock()
    mock_get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=[{"id": "doc1"}]))
    )
    mock_instance.__aenter__.return_value.get = mock_get

    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/?query=malware%20analysis")
        assert response.status_code == 200
        _, called_kwargs = mock_get.call_args
        assert called_kwargs["params"]["query"] == "malware analysis"


@pytest.mark.asyncio
def test_list_documents_include_deleted(client):
    """Test listing documents with deleted items included."""
    mock_instance = MagicMock()
    mock_get = AsyncMock(
        return_value=MagicMock(status_code=200, json=MagicMock(return_value=[{"id": "doc1"}]))
    )
    mock_instance.__aenter__.return_value.get = mock_get

    with patch("httpx.AsyncClient", return_value=mock_instance):
        response = client.get("/api/v1/documents/?include_deleted=true")
        assert response.status_code == 200
        _, called_kwargs = mock_get.call_args
        assert called_kwargs["params"]["include_deleted"] is True
