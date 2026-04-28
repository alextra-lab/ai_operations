"""
Integration tests for B3-F2: Template-Driven RAG Configuration.

Tests comprehensive RAG configuration including:
- rag.enabled check to skip retrieval when disabled
- rag.metadata_filters application to QueryService
- rag.top_k and rag.similarity_threshold verification
- Integration with orchestrator controller

These tests verify that the use case configuration system properly
applies all RAG settings to retrieval operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.app.orchestrator.controller import Orchestrator
from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import RAGConfig, UseCaseConfig


class TestRAGEnabledDisabled:
    """Test RAG enabled/disabled behavior in orchestrator."""

    @pytest.mark.asyncio
    async def test_rag_disabled_skips_retrieval(self):
        """Test that RAG disabled in config skips retrieval entirely."""
        # Create use case config with RAG disabled
        config = UseCaseConfig(rag=RAGConfig(enabled=False))

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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                },
            )

            # Call retrieve_context with RAG disabled
            context = await orchestrator.retrieve_context(
                query="test query", intent_type=RequestType.QUERY, use_case_config=config
            )

            # Verify RAG was skipped
            assert context["sources"] == []
            assert context["metadata"]["rag_enabled"] is False
            assert context["metadata"]["total_sources"] == 0
            assert context["metadata"]["retrieval_time"] == 0.0

    @pytest.mark.asyncio
    async def test_rag_enabled_performs_retrieval(self):
        """Test that RAG enabled in config performs retrieval."""
        # Create use case config with RAG enabled
        config = UseCaseConfig(rag=RAGConfig(enabled=True, top_k=5, similarity_threshold=0.7))

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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                },
            )

            # Mock httpx client for retrieval service call
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "document_id": "doc1",
                            "chunk_id": "chunk1",
                            "score": 0.85,
                            "text_snippet": "Test content",
                            "document_title": "Test Document",
                            "metadata": {"classification": "public"},
                        }
                    ]
                }
                mock_response.raise_for_status = MagicMock()  # Not async

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call retrieve_context with RAG enabled
                context = await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=config
                )

                # Verify retrieval was performed
                assert len(context["sources"]) == 1
                assert context["sources"][0]["document_id"] == "doc1"
                assert context["sources"][0]["relevance_score"] == 0.85

                # Verify config values were used in request
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                assert request_data["top_k"] == 5
                assert request_data["min_relevancy_score"] == 0.7


class TestRAGMetadataFilters:
    """Test RAG metadata filters application."""

    @pytest.mark.asyncio
    async def test_metadata_filters_applied_to_retrieval_request(self):
        """Test that metadata filters are applied to retrieval service request."""
        # Create use case config with metadata filters
        config = UseCaseConfig(
            rag=RAGConfig(
                enabled=True, metadata_filters={"classification": "threat-intel", "source": "nist"}
            )
        )

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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                },
            )

            # Mock httpx client for retrieval service call
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = MagicMock()  # Not async

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call retrieve_context with metadata filters
                await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=config
                )

                # Verify metadata filters were included in request
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                assert "filters" in request_data
                filters = request_data["filters"]

                # Verify filters structure
                assert len(filters) == 2
                filter_dict = {f["field"]: f["value"] for f in filters}
                assert filter_dict["classification"] == "threat-intel"
                assert filter_dict["source"] == "nist"

    @pytest.mark.asyncio
    async def test_no_metadata_filters_when_not_specified(self):
        """Test that no filters are sent when metadata_filters is empty."""
        # Create use case config without metadata filters
        config = UseCaseConfig(rag=RAGConfig(enabled=True, metadata_filters={}))  # Empty filters

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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                },
            )

            # Mock httpx client for retrieval service call
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = MagicMock()  # Not async

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call retrieve_context without metadata filters
                await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=config
                )

                # Verify no filters were included in request
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                assert "filters" not in request_data


class TestRAGConfigValues:
    """Test RAG configuration values application."""

    @pytest.mark.asyncio
    async def test_config_top_k_and_similarity_threshold_applied(self):
        """Test that config top_k and similarity_threshold are applied."""
        # Create use case config with custom values
        config = UseCaseConfig(rag=RAGConfig(enabled=True, top_k=7, similarity_threshold=0.8))

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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                },
            )

            # Mock httpx client for retrieval service call
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = MagicMock()  # Not async

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call retrieve_context with custom config
                await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=config
                )

                # Verify config values were used in request
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                assert request_data["top_k"] == 7
                assert request_data["min_relevancy_score"] == 0.8

    @pytest.mark.asyncio
    async def test_fallback_to_defaults_when_no_config(self):
        """Test that system falls back to defaults when no use case config provided."""
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
                    "retrieval_svc_url": "http://localhost:8004/api/v1",
                    "llm_guard_url": "http://localhost:8082",
                    "jwt_secret": "test_secret",
                    "min_relevancy_score": 0.3,
                },
            )

            # Mock httpx client for retrieval service call
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": []}
                mock_response.raise_for_status = MagicMock()  # Not async

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                # Call retrieve_context without use case config
                await orchestrator.retrieve_context(
                    query="test query", intent_type=RequestType.QUERY, use_case_config=None
                )

                # Verify fallback values were used
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                request_data = call_args[1]["json"]

                # Should use intent-based default from _get_top_k_for_intent
                assert "top_k" in request_data
                assert request_data["top_k"] > 0
                assert request_data["min_relevancy_score"] == 0.3


class TestRAGConfigValidation:
    """Test RAG configuration validation and edge cases."""

    def test_metadata_filters_accepts_various_types(self):
        """Test that metadata_filters accepts various value types."""
        # Test with string values
        config1 = UseCaseConfig(
            rag=RAGConfig(metadata_filters={"classification": "public", "source": "nist"})
        )
        assert config1.rag.metadata_filters["classification"] == "public"

        # Test with numeric values
        config2 = UseCaseConfig(rag=RAGConfig(metadata_filters={"priority": 1, "confidence": 0.95}))
        assert config2.rag.metadata_filters["priority"] == 1
        assert config2.rag.metadata_filters["confidence"] == 0.95

        # Test with boolean values
        config3 = UseCaseConfig(
            rag=RAGConfig(metadata_filters={"is_public": True, "is_verified": False})
        )
        assert config3.rag.metadata_filters["is_public"] is True
        assert config3.rag.metadata_filters["is_verified"] is False

    def test_empty_metadata_filters_is_valid(self):
        """Test that empty metadata_filters is valid."""
        config = UseCaseConfig(rag=RAGConfig(enabled=True, metadata_filters={}))

        assert config.rag.metadata_filters == {}
        assert config.rag.enabled is True

    def test_nested_metadata_filters_structure(self):
        """Test that nested metadata filter structures are handled."""
        config = UseCaseConfig(
            rag=RAGConfig(
                metadata_filters={
                    "metadata.source": "nist",
                    "metadata.classification": "threat-intel",
                    "tags": ["malware", "apt"],
                }
            )
        )

        assert config.rag.metadata_filters["metadata.source"] == "nist"
        assert config.rag.metadata_filters["metadata.classification"] == "threat-intel"
        assert config.rag.metadata_filters["tags"] == ["malware", "apt"]
