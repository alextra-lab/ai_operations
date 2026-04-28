"""
Integration tests for template-driven model selection.

Tests that use case configuration properly overrides model selection,
generation parameters, and embedding models.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.llm import ModelType
from src.orchestrator.app.schemas.use_case_config import (
    GenerationParamsConfig,
    ModelsConfig,
    UseCaseConfig,
)


class TestTemplateModelSelection:
    """Test template-driven model selection functionality."""

    @pytest.fixture
    def mock_use_case_config(self):
        """Create a mock use case config with model overrides."""
        return UseCaseConfig(
            models=ModelsConfig(llm="gpt-4o-mini", embedding="text-embedding-3-large"),
            generation_params=GenerationParamsConfig(temperature=0.3, max_tokens=2048),
        )

    @pytest.fixture
    def mock_default_config(self):
        """Create a mock default config."""
        return UseCaseConfig(
            models=ModelsConfig(llm="gpt-4o", embedding="text-embedding-3-small"),
            generation_params=GenerationParamsConfig(temperature=0.7, max_tokens=1024),
        )

    @pytest.mark.asyncio
    async def test_config_overrides_llm_model(self, mock_use_case_config):
        """Test that config specifies GPT-4o-mini, should use it."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter
        from src.orchestrator.app.schemas.llm import LLMRequest

        # Create LLM request
        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        # Create LLM router
        router = LLMRouter()

        # Apply config overrides
        router._apply_config_overrides(request, mock_use_case_config)

        # Verify model preference was set
        assert request.model_preference == ModelType.QUERY
        assert request.temperature == 0.3
        assert request.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_config_applies_temperature(self, mock_use_case_config):
        """Test that config temperature is applied to LLM call."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter
        from src.orchestrator.app.schemas.llm import LLMRequest

        # Create LLM request with default values
        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        # Create LLM router
        router = LLMRouter()

        # Apply config overrides
        router._apply_config_overrides(request, mock_use_case_config)

        # Verify temperature was overridden
        assert request.temperature == 0.3
        assert request.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_config_applies_embedding_model(self, mock_use_case_config):
        """Test that config embedding model is used."""
        from src.corpus_svc.app.clients.embedding_client import EmbeddingServiceClient
        from src.corpus_svc.app.repositories.document_repository import DocumentRepository
        from src.corpus_svc.app.repositories.usage_stats_repository import UsageStatsRepository
        from src.corpus_svc.app.repositories.vector_repository import QdrantRepository
        from src.corpus_svc.app.services.query_service import QueryService

        # Mock dependencies
        mock_vector_repo = MagicMock(spec=QdrantRepository)
        mock_doc_repo = MagicMock(spec=DocumentRepository)
        mock_usage_repo = MagicMock(spec=UsageStatsRepository)
        mock_embedding_client = MagicMock(spec=EmbeddingServiceClient)

        # Mock embedding response
        mock_embedding_client.embed_texts = AsyncMock(
            return_value=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )

        # Create query service
        query_service = QueryService(
            vector_repository=mock_vector_repo,
            document_repository=mock_doc_repo,
            usage_stats_repository=mock_usage_repo,
            embedding_client=mock_embedding_client,
        )

        # Perform search with embedding model
        await query_service.perform_semantic_search(
            query_text="test query", embedding_model="text-embedding-3-large"
        )

        # Verify embedding client was called with correct model
        mock_embedding_client.embed_texts.assert_called_once_with(
            texts=["test query"], model="text-embedding-3-large", auth_token=None
        )

    @pytest.mark.asyncio
    async def test_config_fallback_to_defaults(self, mock_default_config):
        """Test that fallback to defaults works when config is None."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter
        from src.orchestrator.app.schemas.llm import LLMRequest

        # Create LLM request
        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        # Create LLM router
        router = LLMRouter()

        # Apply config overrides with None config
        router._apply_config_overrides(request, None)

        # Verify no changes were made
        assert request.temperature == 0.7
        assert request.max_tokens == 1024
        assert request.model_preference is None

    @pytest.mark.asyncio
    async def test_model_mapping_handles_unknown_models(self, mock_use_case_config):
        """Test that unknown model names are handled gracefully."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter
        from src.orchestrator.app.schemas.llm import LLMRequest

        # Create config with unknown model
        config_with_unknown_model = UseCaseConfig(
            models=ModelsConfig(llm="unknown-model-name", embedding="text-embedding-3-large"),
            generation_params=GenerationParamsConfig(temperature=0.3, max_tokens=2048),
        )

        # Create LLM request
        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        # Create LLM router
        router = LLMRouter()

        # Apply config overrides
        router._apply_config_overrides(request, config_with_unknown_model)

        # Verify fallback to QUERY model type
        assert request.model_preference == ModelType.QUERY
        assert request.temperature == 0.3
        assert request.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_partial_config_application(self):
        """Test that partial config (only some fields) works correctly."""
        from src.orchestrator.app.orchestrator.llm_router import LLMRouter
        from src.orchestrator.app.schemas.llm import LLMRequest

        # Create config with only temperature override
        partial_config = UseCaseConfig(
            models=ModelsConfig(llm="gpt-4o-mini", embedding=None),
            generation_params=GenerationParamsConfig(temperature=0.2, max_tokens=None),
        )

        # Create LLM request
        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        # Create LLM router
        router = LLMRouter()

        # Apply config overrides
        router._apply_config_overrides(request, partial_config)

        # Verify only temperature was overridden
        assert request.temperature == 0.2
        assert request.max_tokens == 1024  # Should remain unchanged
        assert request.model_preference == ModelType.QUERY

    @pytest.mark.asyncio
    async def test_embedding_model_passed_to_retrieval_service(self, mock_use_case_config):
        """Test that embedding model is passed to retrieval service."""

        from src.orchestrator.app.orchestrator.controller import Orchestrator

        # Mock database session
        mock_db = MagicMock()

        # Create orchestrator
        orchestrator = Orchestrator(db=mock_db)

        # Mock the retrieval service call
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Call retrieve_context with use case config
            await orchestrator.retrieve_context(
                query="test query",
                intent_type=RequestType.QUERY,
                use_case_config=mock_use_case_config,
            )

            # Verify the request was made with embedding model
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_data = call_args[1]["json"]
            assert request_data["embedding_model"] == "text-embedding-3-large"

    @pytest.mark.asyncio
    async def test_no_embedding_model_when_config_missing(self, mock_default_config):
        """Test that no embedding model is passed when config doesn't specify one."""

        from src.orchestrator.app.orchestrator.controller import Orchestrator

        # Mock database session
        mock_db = MagicMock()

        # Create orchestrator
        orchestrator = Orchestrator(db=mock_db)

        # Mock the retrieval service call
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Call retrieve_context with config that has no embedding model
            config_no_embedding = UseCaseConfig(
                models=ModelsConfig(llm="gpt-4o", embedding=None),
                generation_params=GenerationParamsConfig(temperature=0.7, max_tokens=1024),
            )

            await orchestrator.retrieve_context(
                query="test query",
                intent_type=RequestType.QUERY,
                use_case_config=config_no_embedding,
            )

            # Verify the request was made without embedding model
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            request_data = call_args[1]["json"]
            assert "embedding_model" not in request_data
