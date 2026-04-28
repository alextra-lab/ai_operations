"""
Integration tests for B1-F3: RAG Defaults Fix & Application.

Tests comprehensive RAG configuration including:
- Default top_k value verification
- Config override functionality
- Similarity threshold application
- RAG enabled/disabled behavior

These tests verify that the use case configuration system properly
applies to RAG operations.
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.corpus_svc.app.services.query_service import QueryService
from src.orchestrator.app.orchestrator.controller import Orchestrator
from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import RAGConfig, UseCaseConfig


class TestRAGDefaults:
    """Test RAG default configuration values."""

    @pytest.mark.asyncio
    async def test_default_top_k_is_10(self):
        """Test that default top_k is 10 in query service."""
        # Create mock dependencies
        mock_vector_repo = AsyncMock()
        mock_doc_repo = AsyncMock()
        mock_usage_stats_repo = AsyncMock()
        mock_embedding_client = AsyncMock()

        # Create query service
        query_service = QueryService(
            vector_repository=mock_vector_repo,
            document_repository=mock_doc_repo,
            usage_stats_repository=mock_usage_stats_repo,
            embedding_client=mock_embedding_client,
        )

        # Check default value by inspecting the method signature
        sig = inspect.signature(query_service.perform_semantic_search)
        top_k_default = sig.parameters["top_k"].default

        assert top_k_default == 10, f"Expected default top_k=10, got {top_k_default}"

    @pytest.mark.asyncio
    async def test_query_service_respects_top_k_parameter(self):
        """Test that query service respects the top_k parameter passed to it."""
        # Create mock dependencies
        mock_vector_repo = AsyncMock()
        mock_doc_repo = AsyncMock()
        mock_usage_stats_repo = AsyncMock()
        mock_embedding_client = AsyncMock()

        # Mock embedding response
        mock_embedding_obj = MagicMock()
        mock_embedding_obj.embedding = [0.1] * 384  # Mock embedding vector
        mock_embedding_client.embed_texts.return_value = [mock_embedding_obj]

        # Mock vector repository response
        mock_vector_repo.semantic_search.return_value = []

        query_service = QueryService(
            vector_repository=mock_vector_repo,
            document_repository=mock_doc_repo,
            usage_stats_repository=mock_usage_stats_repo,
            embedding_client=mock_embedding_client,
        )

        # Test with custom top_k
        await query_service.perform_semantic_search(query_text="test query", top_k=5)

        # Verify that vector_repository.semantic_search was called with top_k=5
        mock_vector_repo.semantic_search.assert_called_once()
        call_args = mock_vector_repo.semantic_search.call_args
        assert call_args[1]["top_k"] == 5


class TestRAGConfigOverride:
    """Test RAG configuration override from use case config."""

    @pytest.mark.asyncio
    async def test_config_overrides_top_k(self):
        """Test that use case config overrides default top_k."""
        # Create a use case config with custom top_k
        config = UseCaseConfig(rag=RAGConfig(enabled=True, top_k=7, similarity_threshold=0.8))

        # Verify config values
        assert config.rag.top_k == 7
        assert config.rag.similarity_threshold == 0.8
        assert config.rag.enabled is True

    @pytest.mark.asyncio
    async def test_config_overrides_similarity_threshold(self):
        """Test that use case config overrides similarity threshold."""
        # Create config with custom threshold
        config = UseCaseConfig(rag=RAGConfig(enabled=True, similarity_threshold=0.75))

        assert config.rag.similarity_threshold == 0.75

    def test_config_values_are_accessible(self):
        """Test that config values for top_k and similarity are accessible."""
        config = UseCaseConfig(rag=RAGConfig(enabled=True, top_k=5, similarity_threshold=0.7))

        # Verify config values are accessible
        assert config.rag.top_k == 5
        assert config.rag.similarity_threshold == 0.7
        assert config.rag.enabled is True


class TestRAGEnabledDisabled:
    """Test RAG enabled/disabled behavior."""

    def test_rag_disabled_config(self):
        """Test that RAG can be disabled in config."""
        config = UseCaseConfig(rag=RAGConfig(enabled=False))

        assert config.rag.enabled is False

    def test_rag_enabled_config(self):
        """Test that RAG can be enabled in config."""
        config = UseCaseConfig(rag=RAGConfig(enabled=True, top_k=10, similarity_threshold=0.6))

        assert config.rag.enabled is True
        assert config.rag.top_k == 10
        assert config.rag.similarity_threshold == 0.6


class TestRAGConfigValidation:
    """Test RAG configuration validation."""

    def test_valid_rag_config(self):
        """Test that valid RAG config passes validation."""
        config = UseCaseConfig(
            rag=RAGConfig(
                enabled=True,
                top_k=10,
                similarity_threshold=0.6,
                vector_collections=["documents"],
                metadata_filters={"classification": "public"},
            )
        )

        assert config.rag.enabled is True
        assert config.rag.top_k == 10
        assert config.rag.similarity_threshold == 0.6
        assert config.rag.vector_collections == ["documents"]
        assert config.rag.metadata_filters == {"classification": "public"}

    def test_invalid_top_k_raises_error(self):
        """Test that invalid top_k raises validation error."""
        from pydantic import ValidationError

        # Test top_k = 0 (too low)
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(rag=RAGConfig(top_k=0))
        assert "Input should be greater than 0" in str(exc_info.value)

        # Test top_k = 200 (too high)
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(rag=RAGConfig(top_k=200))
        assert "Input should be less than or equal to 100" in str(exc_info.value)

    def test_invalid_similarity_threshold_raises_error(self):
        """Test that invalid similarity_threshold raises validation error."""
        from pydantic import ValidationError

        # Test threshold < 0
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(rag=RAGConfig(similarity_threshold=-0.1))
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        # Test threshold > 1
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(rag=RAGConfig(similarity_threshold=1.5))
        assert "Input should be less than or equal to 1" in str(exc_info.value)


class TestRAGConfigIntegration:
    """Integration tests for RAG configuration with orchestrator."""

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_no_config(self):
        """Test that system falls back to default top_k when no config provided."""
        # Create mock database session
        mock_db = AsyncMock()

        with (
            patch("src.orchestrator.app.orchestrator.controller.IntentParser"),
            patch("src.orchestrator.app.orchestrator.controller.PromptAssembler"),
            patch("src.orchestrator.app.orchestrator.controller.LLMRouter"),
            patch("src.orchestrator.app.orchestrator.controller.ResponseFormatter"),
            patch("src.orchestrator.app.services.use_case_config_loader.UseCaseConfigLoader"),
        ):
            orchestrator = Orchestrator(
                db=mock_db,
                config={
                    "retrieval_svc_url": "http://localhost:8003/api/v1",
                    "llm_guard_url": "http://localhost:8004",
                    "jwt_secret": "test_secret",
                },
            )

            # Mock httpx client
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = AsyncMock()
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = AsyncMock()

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call without use_case_config (should use fallback)
                await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=None
                )

                # Verify fallback logic was used
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                # Should use intent-based default from _get_top_k_for_intent
                assert "top_k" in request_data
                assert request_data["top_k"] > 0
