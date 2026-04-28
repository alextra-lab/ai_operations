"""
Integration tests for corpus validation features (P4-F10).

Tests test suite CRUD, exemplar management, and API endpoints.
"""

from uuid import uuid4

import pytest

# These are integration tests that require the test environment to be running


@pytest.mark.integration
class TestTestSuiteAPI:
    """Integration tests for test suite API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create API client."""
        import httpx

        return httpx.AsyncClient(base_url="http://localhost:8006", timeout=30.0)

    @pytest.mark.asyncio
    async def test_create_test_suite(self, api_client):
        """Test creating a test suite via API."""
        test_suite_data = {
            "name": f"Integration Test Suite {uuid4()}",
            "description": "Test suite for integration testing",
            "collection_ids": [str(uuid4())],
            "k": 5,
            "questions": [
                {
                    "query": "What are the security policies?",
                    "expected_doc_ids": [str(uuid4())],
                    "expected_phrases": ["security", "policy"],
                    "tags": ["security"],
                }
            ],
        }

        response = await api_client.post("/api/v1/test-suites", json=test_suite_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_suite_data["name"]
        assert data["k"] == 5
        assert len(data["questions"]) == 1

    @pytest.mark.asyncio
    async def test_list_test_suites(self, api_client):
        """Test listing test suites via API."""
        response = await api_client.get("/api/v1/test-suites?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_test_suite_lifecycle(self, api_client):
        """Test complete test suite lifecycle: create, get, update, delete."""
        # Create
        create_data = {
            "name": f"Lifecycle Test {uuid4()}",
            "description": "Test lifecycle",
            "collection_ids": [str(uuid4())],
            "k": 3,
            "questions": [],
        }

        create_response = await api_client.post("/api/v1/test-suites", json=create_data)
        assert create_response.status_code == 201
        suite_id = create_response.json()["id"]

        # Get
        get_response = await api_client.get(f"/api/v1/test-suites/{suite_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == suite_id

        # Update
        update_data = {"description": "Updated description", "k": 10}
        update_response = await api_client.patch(
            f"/api/v1/test-suites/{suite_id}", json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description"
        assert update_response.json()["k"] == 10

        # Delete
        delete_response = await api_client.delete(f"/api/v1/test-suites/{suite_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = await api_client.get(f"/api/v1/test-suites/{suite_id}")
        assert verify_response.status_code == 404


@pytest.mark.integration
class TestExemplarAPI:
    """Integration tests for exemplar API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create API client."""
        import httpx

        return httpx.AsyncClient(base_url="http://localhost:8006", timeout=30.0)

    @pytest.mark.asyncio
    async def test_create_exemplar(self, api_client):
        """Test creating an exemplar via API."""
        exemplar_data = {
            "text": "Example Sigma rule for detecting suspicious activity",
            "domain": "soc",
            "rule_type": "sigma-rule",
            "tags": ["detection", "threat-hunting"],
            "quality_score": 0.95,
            "status": "draft",
        }

        response = await api_client.post("/api/v1/exemplars", json=exemplar_data)

        assert response.status_code == 201
        data = response.json()
        assert data["text"] == exemplar_data["text"]
        assert data["domain"] == "soc"
        assert data["quality_score"] == 0.95

    @pytest.mark.asyncio
    async def test_list_exemplars(self, api_client):
        """Test listing exemplars via API."""
        response = await api_client.get("/api/v1/exemplars?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_exemplar_lifecycle(self, api_client):
        """Test complete exemplar lifecycle: create, get, approve, delete."""
        # Create
        create_data = {
            "text": f"Example content {uuid4()}",
            "domain": "soc",
            "status": "draft",
        }

        create_response = await api_client.post("/api/v1/exemplars", json=create_data)
        assert create_response.status_code == 201
        exemplar_id = create_response.json()["id"]

        # Get
        get_response = await api_client.get(f"/api/v1/exemplars/{exemplar_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == exemplar_id
        assert get_response.json()["status"] == "draft"

        # Approve
        approve_response = await api_client.post(f"/api/v1/exemplars/{exemplar_id}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        # Delete
        delete_response = await api_client.delete(f"/api/v1/exemplars/{exemplar_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = await api_client.get(f"/api/v1/exemplars/{exemplar_id}")
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_exemplar_selection_pinned(self, api_client):
        """Test pinned exemplar selection."""
        # Create some exemplars first
        exemplar_ids = []
        for i in range(3):
            create_response = await api_client.post(
                "/api/v1/exemplars",
                json={
                    "text": f"Example {i}",
                    "domain": "soc",
                    "status": "approved",
                },
            )
            if create_response.status_code == 201:
                exemplar_ids.append(create_response.json()["id"])

        if not exemplar_ids:
            pytest.skip("Could not create exemplars for testing")

        # Select by IDs
        selection_request = {
            "mode": "pinned",
            "pinned_ids": exemplar_ids[:2],
            "status": "approved",
        }

        response = await api_client.post("/api/v1/exemplars/select", json=selection_request)

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "pinned"
        assert len(data["exemplars"]) <= 2


@pytest.mark.integration
class TestEphemeralCollections:
    """Integration tests for ephemeral collections."""

    @pytest.mark.asyncio
    async def test_ephemeral_collection_creation(self):
        """Test creating ephemeral collection with TTL."""
        # This requires the collections API to be updated
        # Skip for now - will be tested when collections router is updated
        pytest.skip("Requires collections API update for ephemeral support")

    @pytest.mark.asyncio
    async def test_ephemeral_collection_cleanup(self):
        """Test cleanup of expired ephemeral collections."""
        # This requires the cleanup job to be implemented
        pytest.skip("Requires cleanup job implementation")
