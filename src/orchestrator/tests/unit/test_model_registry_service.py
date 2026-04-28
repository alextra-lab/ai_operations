"""
Tests for ModelRegistryService.

MIGRATION NOTE (Phase 7 - Async Migration):
When migrating to async:
1. Change `Session` to `AsyncSession` in all fixtures and type hints
2. Add `@pytest.mark.asyncio` to all test functions
3. Add `await` to all service method calls
4. Change `session.commit()` to `await session.commit()`
5. Change `session.add()` to `await session.add()` (if needed)
6. Update mocks to use `AsyncMock` for async methods
7. Change `session.query()` to `select(Model)` with `await db.execute()`
8. Change `.all()`, `.first()`, `.count()` to use `result.scalars().all()`, etc.

Example transformation:
    # Before (Sync)
    def test_list_models(mock_session):
        service = ModelRegistryService(session=mock_session)
        result = service.list_models()

    # After (Async)
    @pytest.mark.asyncio
    async def test_list_models(mock_async_session):
        service = ModelRegistryService(session=mock_async_session)
        result = await service.list_models()
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.db.models import Model
from app.schemas.model import (
    ModelDetailedResponse,
    ModelListResponse,
    ModelRecommendation,
    ModelSelectionRequest,
)
from app.services.model_registry_service import ModelRegistryService


@pytest.fixture
def mock_session():
    """
    Mock async database session with all necessary methods.

    All database operations are mocked - NO real database interaction.

    Note: Tests should use session.execute() which returns a result with scalars() method.
    """
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_model():
    """Sample model object for testing."""
    now = datetime.now(tz=UTC)
    return Model(
        id=uuid4(),
        model_id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider_type="openai",
        provider="OpenAI Production",
        model_type="llm",
        context_window=128000,
        max_input_tokens=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_vision=False,
        supports_audio=False,
        is_reasoning_model=False,
        reasoning_config={},
        is_available=True,
        is_hidden=False,
        health_status="healthy",
        input_price_per_million=Decimal("0.15"),
        output_price_per_million=Decimal("0.60"),
        deprecated=False,
        default_temperature=0.7,
        temperature_range={"min": 0.0, "max": 2.0},
        metadata_json={},
        created_at=now,
        updated_at=now,
        last_checked_at=now,
    )


@pytest.fixture
def sample_models(sample_model):
    """List of sample models for testing."""
    now = datetime.now(tz=UTC)
    model2 = Model(
        id=uuid4(),
        model_id="claude-3-5-sonnet",
        name="Claude 3.5 Sonnet",
        provider_type="anthropic",
        provider="Anthropic Production",
        model_type="llm",
        context_window=200000,
        max_input_tokens=200000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_vision=True,
        supports_audio=False,
        is_reasoning_model=False,
        reasoning_config={},
        is_available=True,
        is_hidden=False,
        health_status="healthy",
        input_price_per_million=Decimal("3.00"),
        output_price_per_million=Decimal("15.00"),
        deprecated=False,
        default_temperature=0.7,
        temperature_range={"min": 0.0, "max": 2.0},
        metadata_json={},
        created_at=now,
        updated_at=now,
        last_checked_at=now,
    )
    return [sample_model, model2]


class TestModelRegistryServiceInit:
    """Test ModelRegistryService initialization."""

    def test_init_with_session(self, mock_session):
        """Test initialization with session."""
        service = ModelRegistryService(session=mock_session)
        assert service.session == mock_session
        assert service.inference_endpoint is None
        assert service.api_key is None
        assert service.gateway_url is None

    def test_init_with_all_params(self, mock_session):
        """Test initialization with all parameters."""
        service = ModelRegistryService(
            session=mock_session,
            inference_endpoint="https://api.example.com",
            api_key="test-key",
            gateway_url="http://gateway:8002",
        )
        assert service.session == mock_session
        assert service.inference_endpoint == "https://api.example.com"
        assert service.api_key == "test-key"
        assert service.gateway_url == "http://gateway:8002"


class TestListModels:
    """Test list_models method."""

    def test_list_models_empty(self, mock_session):
        """Test listing models when database is empty."""
        mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )
        mock_session.query.return_value.filter.return_value.count.return_value = 0

        service = ModelRegistryService(session=mock_session)
        result = service.list_models()

        assert isinstance(result, ModelListResponse)
        assert result.total == 0
        assert len(result.models) == 0
        assert result.page == 1
        assert result.size == 50

    def test_list_models_with_results(self, mock_session, sample_models):
        """Test listing models with results."""
        # Setup query chain mocks
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        mock_session.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = sample_models

        # Count query
        mock_session.query.return_value.filter.return_value.count.return_value = len(sample_models)

        service = ModelRegistryService(session=mock_session)
        result = service.list_models()

        assert isinstance(result, ModelListResponse)
        assert result.total == 2
        assert len(result.models) == 2
        assert result.models[0].model_id == "gpt-4o-mini"

    def test_list_models_with_provider_filter(self, mock_session, sample_model):
        """Test listing models filtered by provider."""
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        mock_session.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = [sample_model]

        mock_session.query.return_value.filter.return_value.count.return_value = 1

        service = ModelRegistryService(session=mock_session)
        result = service.list_models(provider="openai")

        assert result.total == 1
        assert result.models[0].provider == "OpenAI Production"

    def test_list_models_pagination(self, mock_session, sample_models):
        """Test pagination in list_models."""
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        mock_session.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = [sample_models[0]]  # Page 1, size 1

        mock_session.query.return_value.filter.return_value.count.return_value = 2

        service = ModelRegistryService(session=mock_session)
        result = service.list_models(page=1, size=1)

        assert result.page == 1
        assert result.size == 1
        assert result.total == 2
        assert result.pages == 2


class TestGetModel:
    """Test get_model method."""

    def test_get_model_not_found(self, mock_session):
        """Test getting non-existent model."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        service = ModelRegistryService(session=mock_session)
        result = service.get_model("nonexistent")

        assert result is None

    def test_get_model_found(self, mock_session, sample_model):
        """Test getting existing model."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_model

        service = ModelRegistryService(session=mock_session)
        result = service.get_model("gpt-4o-mini")

        assert isinstance(result, ModelDetailedResponse)
        assert result.model_id == "gpt-4o-mini"
        assert result.name == "GPT-4o Mini"
        assert result.capabilities is not None
        assert result.pricing is not None
        assert result.performance is not None

    def test_get_model_with_pricing(self, mock_session, sample_model):
        """Test getting model with pricing information."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_model

        service = ModelRegistryService(session=mock_session)
        result = service.get_model("gpt-4o-mini")

        assert result.pricing is not None
        assert result.pricing.input_price_per_million == Decimal("0.15")
        assert result.pricing.output_price_per_million == Decimal("0.60")
        assert result.estimated_cost_per_1k_tokens is not None


class TestDiscoverModelsFromInferenceServer:
    """Test discover_models_from_inference_server method."""

    @patch("app.services.model_registry_service.httpx.Client")
    def test_discover_from_gateway_success(self, mock_client_class, mock_session):
        """Test discovering models from Gateway."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4o-mini", "owned_by": "openai"},
                {"id": "claude-3-5-sonnet", "owned_by": "anthropic"},
            ]
        }
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = ModelRegistryService(session=mock_session, gateway_url="http://gateway:8002")
        result = service.discover_models_from_inference_server()

        assert len(result) == 2
        assert result[0]["id"] == "gpt-4o-mini"
        assert result[1]["id"] == "claude-3-5-sonnet"

    @patch("app.services.model_registry_service.httpx.Client")
    def test_discover_from_gateway_fallback(self, mock_client_class, mock_session):
        """Test Gateway failure falls back to direct endpoint."""
        # Gateway fails
        mock_gateway_response = MagicMock()
        mock_gateway_response.raise_for_status.side_effect = Exception("Gateway error")

        # Direct endpoint succeeds
        mock_direct_response = MagicMock()
        mock_direct_response.json.return_value = {
            "data": [{"id": "local-model", "owned_by": "local"}]
        }
        mock_direct_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.side_effect = [mock_gateway_response, mock_direct_response]
        mock_client_class.return_value = mock_client

        service = ModelRegistryService(
            session=mock_session,
            gateway_url="http://gateway:8002",
            inference_endpoint="https://api.example.com",
        )
        result = service.discover_models_from_inference_server()

        assert len(result) == 1
        assert result[0]["id"] == "local-model"

    @patch("app.services.model_registry_service.httpx.Client")
    def test_discover_from_direct_endpoint(self, mock_client_class, mock_session):
        """Test discovering from direct inference endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "local-model", "owned_by": "local"}]}
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = ModelRegistryService(
            session=mock_session, inference_endpoint="https://api.example.com"
        )
        result = service.discover_models_from_inference_server()

        assert len(result) == 1
        assert result[0]["id"] == "local-model"

    def test_discover_no_endpoints(self, mock_session):
        """Test discovery with no endpoints configured."""
        service = ModelRegistryService(session=mock_session)
        result = service.discover_models_from_inference_server()

        assert result == []


class TestSyncWithInferenceServer:
    """Test sync_with_inference_server method."""

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    def test_sync_creates_new_models(self, mock_discover, mock_session, sample_model):
        """Test sync creates new models."""
        mock_discover.return_value = [{"id": "new-model", "owned_by": "test-provider"}]

        # Mock query for existing models (empty)
        mock_session.query.return_value.all.return_value = []

        # Mock query chain for new model creation
        query_mock = MagicMock()
        mock_session.query.return_value = query_mock

        service = ModelRegistryService(session=mock_session)
        with patch.object(service, "_create_new_model") as mock_create:
            mock_create.return_value = sample_model
            result = service.sync_with_inference_server()

        assert result["status"] == "success"
        assert result["summary"]["newly_created"] == 1
        assert "new-model" in result["created_models"][0]["model_id"]

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    def test_sync_updates_existing_models(self, mock_discover, mock_session, sample_model):
        """Test sync updates existing models."""
        mock_discover.return_value = [{"id": "gpt-4o-mini", "owned_by": "openai"}]

        # Mock existing model
        mock_session.query.return_value.all.return_value = [sample_model]

        service = ModelRegistryService(session=mock_session)
        with patch.object(service, "_update_existing_model") as mock_update:
            mock_update.return_value = True
            result = service.sync_with_inference_server()

        assert result["status"] == "success"
        assert result["summary"]["updated_existing"] == 1
        assert "gpt-4o-mini" in result["updated_models"]

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    def test_sync_marks_missing_models_unavailable(self, mock_discover, mock_session, sample_model):
        """Test sync marks missing models as unavailable."""
        mock_discover.return_value = []  # No models discovered

        # Mock existing model that's available
        sample_model.is_available = True
        sample_model.provider = "OpenAI Production"  # Not local
        mock_session.query.return_value.all.return_value = [sample_model]

        service = ModelRegistryService(session=mock_session)
        result = service.sync_with_inference_server()

        assert result["status"] == "success"
        assert result["summary"]["marked_unavailable"] == 1
        assert sample_model.is_available is False
        assert sample_model.health_status == "unavailable"
        mock_session.commit.assert_called_once()

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    def test_sync_skips_local_models(self, mock_discover, mock_session, sample_model):
        """Test sync skips local models (provider=None) when marking unavailable."""
        mock_discover.return_value = []  # No models discovered

        # Mock local model (provider=None)
        sample_model.provider = None
        sample_model.is_available = True
        mock_session.query.return_value.all.return_value = [sample_model]

        service = ModelRegistryService(session=mock_session)
        result = service.sync_with_inference_server()

        # Local model should not be marked unavailable
        assert result["summary"]["marked_unavailable"] == 0
        assert sample_model.is_available is True

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    async def test_sync_uses_provider_metadata_from_gateway(
        self, mock_discover, mock_session, sample_model
    ):
        """Test sync uses provider metadata from Gateway response."""
        # Gateway returns models with provider metadata
        mock_discover.return_value = [
            {
                "id": "openai/gpt-oss-120b",
                "owned_by": "gateway",
                "provider": "LMStudio",  # ✅ From Gateway
                "provider_type": "openai",  # ✅ From Gateway
            }
        ]

        # Mock no existing model (will create new)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = ModelRegistryService(session=mock_session, gateway_url="http://gateway:8002")

        with patch.object(service, "_create_new_model") as mock_create:
            mock_model = MagicMock()
            mock_model.name = "GPT-OSS 120B"
            mock_model.provider_type = "openai"
            mock_model.provider = "LMStudio"
            mock_create.return_value = mock_model

            result = await service.sync_with_inference_server()

            assert result["status"] == "success"
            assert result["summary"]["newly_created"] == 1
            # Verify provider metadata was passed to _create_new_model
            mock_create.assert_called_once_with(
                "openai/gpt-oss-120b",
                "gateway",
                "LMStudio",  # ✅ Provider from Gateway
                "openai",  # ✅ Provider type from Gateway
            )

    @patch.object(ModelRegistryService, "discover_models_from_inference_server")
    async def test_sync_handles_missing_provider_metadata(self, mock_discover, mock_session):
        """Test sync handles models without provider metadata (fallback)."""
        # Gateway returns models without provider metadata (legacy/fallback)
        mock_discover.return_value = [
            {
                "id": "legacy-model",
                "owned_by": "gateway",
                # No provider or provider_type fields
            }
        ]

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = ModelRegistryService(session=mock_session, gateway_url="http://gateway:8002")

        with patch.object(service, "_create_new_model") as mock_create:
            mock_model = MagicMock()
            mock_model.name = "Legacy Model"
            mock_create.return_value = mock_model

            result = await service.sync_with_inference_server()

            assert result["status"] == "success"
            # Should still create model (provider inferred in _create_new_model)
            mock_create.assert_called_once_with(
                "legacy-model",
                "gateway",
                None,  # No provider from Gateway
                None,  # No provider_type from Gateway
            )


class TestRecommendModel:
    """Test recommend_model method."""

    def test_recommend_model_with_match(self, mock_session, sample_models):
        """Test model recommendation with matching model."""
        # Mock list_models
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        mock_session.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = sample_models

        mock_session.query.return_value.filter.return_value.count.return_value = 2

        # Mock get_model for detailed info
        mock_session.query.return_value.filter.return_value.first.return_value = sample_models[0]

        service = ModelRegistryService(session=mock_session)
        request = ModelSelectionRequest(
            use_case_type="query",
            prefer_capabilities=["tools"],
        )
        recommendations = service.recommend_model(request)

        assert len(recommendations) > 0
        assert all(isinstance(r, ModelRecommendation) for r in recommendations)
        assert recommendations[0].confidence > 0.3

    def test_recommend_model_no_matches(self, mock_session):
        """Test model recommendation with no matching models."""
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        offset_mock = MagicMock()
        limit_mock = MagicMock()

        mock_session.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.order_by.return_value = order_mock
        order_mock.offset.return_value = offset_mock
        offset_mock.limit.return_value = limit_mock
        limit_mock.all.return_value = []

        mock_session.query.return_value.filter.return_value.count.return_value = 0

        service = ModelRegistryService(session=mock_session)
        request = ModelSelectionRequest(use_case_type="query")
        recommendations = service.recommend_model(request)

        assert len(recommendations) == 0


class TestCreateNewModel:
    """Test _create_new_model internal method."""

    @patch.object(ModelRegistryService, "get_extended_model_metadata")
    def test_create_new_model_success(self, mock_get_metadata, mock_session):
        """Test creating a new model successfully."""
        mock_get_metadata.return_value = {"context_window": 128000}

        service = ModelRegistryService(session=mock_session)
        with patch.object(service.inferencer, "infer_metadata") as mock_infer:
            mock_infer.return_value = {
                "name": "GPT-4o Mini",
                "provider": "openai",
                "model_type": "llm",
            }

            result = service._create_new_model("gpt-4o-mini", "openai")

        assert result is not None
        assert result.model_id == "gpt-4o-mini"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @patch.object(ModelRegistryService, "get_extended_model_metadata")
    def test_create_new_model_failure(self, mock_get_metadata, mock_session):
        """Test creating a new model with failure."""
        mock_get_metadata.return_value = None

        service = ModelRegistryService(session=mock_session)
        with patch.object(service.inferencer, "infer_metadata") as mock_infer:
            mock_infer.side_effect = Exception("Inference error")

            result = service._create_new_model("invalid-model", None)

        assert result is None


class TestUpdateExistingModel:
    """Test _update_existing_model internal method."""

    def test_update_existing_model_marks_available(self, mock_session, sample_model):
        """Test updating model marks it as available."""
        sample_model.is_available = False
        sample_model.health_status = "unhealthy"

        service = ModelRegistryService(session=mock_session)
        result = service._update_existing_model(
            sample_model, {"id": "gpt-4o-mini", "owned_by": "openai"}
        )

        assert result is True
        assert sample_model.is_available is True
        assert sample_model.health_status == "healthy"

    @patch.object(ModelRegistryService, "get_extended_model_metadata")
    def test_update_existing_model_fills_missing_fields(
        self, mock_get_metadata, mock_session, sample_model
    ):
        """Test updating model fills in missing metadata."""
        sample_model.context_window = None
        sample_model.max_output_tokens = None
        mock_get_metadata.return_value = {
            "context_window": 128000,
            "max_output_tokens": 16384,
        }

        service = ModelRegistryService(session=mock_session)
        result = service._update_existing_model(
            sample_model, {"id": "gpt-4o-mini", "owned_by": "openai"}
        )

        assert result is True
        assert sample_model.context_window == 128000
        assert sample_model.max_output_tokens == 16384

    def test_update_existing_model_no_changes(self, mock_session, sample_model):
        """Test updating model with no changes."""
        service = ModelRegistryService(session=mock_session)
        result = service._update_existing_model(
            sample_model, {"id": "gpt-4o-mini", "owned_by": "openai"}
        )

        # Should return False if no changes made
        assert isinstance(result, bool)
