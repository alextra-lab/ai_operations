"""
Unit tests for cost_estimator utility.

Tests cost estimation functionality for various LLM models.
"""

from unittest.mock import patch

import pytest

from src.orchestrator.app.utils.cost_estimator import _normalize_model_id, estimate_cost


class TestCostEstimator:
    """Test suite for cost estimation utility."""

    @pytest.mark.asyncio
    async def test_estimate_cost_env_defaults(self, monkeypatch):
        """Estimate cost uses EUR env defaults when no DB pricing is available."""
        # Arrange
        model_id = "gpt-4o-mini"
        tokens_in = 1_000_000
        tokens_out = 500_000
        monkeypatch.setenv("PRICING_DEFAULT_INPUT_PER_MILLION", "1.50")
        monkeypatch.setenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", "2.50")

        # Act
        result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)

        # Assert
        assert result["input_cost"] == pytest.approx(1.50, rel=1e-6)
        assert result["output_cost"] == pytest.approx(1.25, rel=1e-6)
        assert result["total_cost"] == pytest.approx(2.75, rel=1e-6)
        assert result["currency"] == "EUR"
        assert result["pricing_source"] == "environment_default"
        assert "pricing_per_million" in result

    @pytest.mark.asyncio
    async def test_estimate_cost_generic_default_unknown_model(self, monkeypatch):
        """Unknown models fall back to generic EUR defaults if env unset."""
        # Arrange
        model_id = "unknown-model-xyz"
        tokens_in = 1_000_000
        tokens_out = 1_000_000
        monkeypatch.delenv("PRICING_DEFAULT_INPUT_PER_MILLION", raising=False)
        monkeypatch.delenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", raising=False)

        # Mock the database module to raise ImportError when AsyncSessionLocal is accessed
        # This simulates the database not being available
        with patch("app.utils.cost_estimator.AsyncSessionLocal", new=None):
            # Also patch the import statement to raise ImportError
            import sys

            original_modules = sys.modules.copy()
            try:
                # Remove the database module from cache to force re-import
                if "app.db.database" in sys.modules:
                    del sys.modules["app.db.database"]
                # Patch __import__ to raise for this specific import
                import builtins

                original_import = builtins.__import__

                def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
                    if (
                        name.endswith("db.database")
                        and fromlist
                        and "AsyncSessionLocal" in fromlist
                    ):
                        raise ImportError("No DB")
                    return original_import(name, globals, locals, fromlist, level)

                builtins.__import__ = mock_import
                try:
                    # Act - this will trigger the import inside _get_model_pricing
                    result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)
                finally:
                    builtins.__import__ = original_import
                    sys.modules.update(original_modules)

                # Assert
                assert result["input_cost"] == pytest.approx(1.0, rel=1e-6)
                assert result["output_cost"] == pytest.approx(2.0, rel=1e-6)
                assert result["total_cost"] == pytest.approx(3.0, rel=1e-6)
                assert result["currency"] == "EUR"
                assert result["pricing_source"] == "generic_default"
            finally:
                sys.modules.update(original_modules)

    @pytest.mark.asyncio
    async def test_estimate_cost_small_usage(self):
        """Test cost estimation with small token counts."""
        # Arrange
        model_id = "gpt-3.5-turbo"
        tokens_in = 1000  # 1K tokens
        tokens_out = 500  # 500 tokens

        # Act
        result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)

        # Assert
        # Should be very small fractions of a cent
        assert result["input_cost"] < 0.01
        assert result["output_cost"] < 0.01
        assert result["total_cost"] < 0.01
        assert result["total_cost"] > 0.0

    @pytest.mark.asyncio
    async def test_estimate_cost_zero_tokens(self, monkeypatch):
        """Cost is zero when there are no tokens."""
        # Arrange
        model_id = "gpt-4o-mini"
        tokens_in = 0
        tokens_out = 0
        monkeypatch.setenv("PRICING_DEFAULT_INPUT_PER_MILLION", "1.00")
        monkeypatch.setenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", "2.00")

        # Mock the database import to raise ImportError when trying to import AsyncSessionLocal
        import builtins

        original_import = builtins.__import__

        def selective_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Only raise for the specific import we want to block
            if name == "app.db.database" and fromlist and "AsyncSessionLocal" in fromlist:
                raise ImportError("No DB")
            return original_import(name, globals, locals, fromlist, level)

        with patch.object(builtins, "__import__", side_effect=selective_import):
            # Act
            result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)

            # Assert
            assert result["total_cost"] == 0.0

    def test_normalize_model_id_with_provider_prefix(self):
        """Provider prefix is removed."""
        # Arrange & Act
        normalized = _normalize_model_id("openai/gpt-4o-mini")

        # Assert
        assert normalized == "gpt-4o-mini"

    def test_normalize_model_id_exact_match(self):
        """Exact model IDs are returned as-is once prefix is removed."""
        # Arrange & Act
        normalized = _normalize_model_id("gpt-4o-mini")

        # Assert
        assert normalized == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_cost_estimate_structure(self, monkeypatch):
        """Result structure includes required fields."""
        # Arrange
        model_id = "gpt-4o-mini"
        tokens_in = 1000
        tokens_out = 500
        monkeypatch.setenv("PRICING_DEFAULT_INPUT_PER_MILLION", "1.00")
        monkeypatch.setenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", "2.00")

        # Act
        result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)

        # Assert
        assert "input_cost" in result
        assert "output_cost" in result
        assert "total_cost" in result
        assert "currency" in result
        assert "pricing_source" in result
        assert "pricing_per_million" in result
        assert "input" in result["pricing_per_million"]
        assert "output" in result["pricing_per_million"]

    @pytest.mark.asyncio
    async def test_cost_rounding(self, monkeypatch):
        """Values are rounded to 6 decimal places."""
        # Arrange
        model_id = "gpt-4o-mini"
        tokens_in = 123
        tokens_out = 456
        monkeypatch.setenv("PRICING_DEFAULT_INPUT_PER_MILLION", "1.00")
        monkeypatch.setenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", "2.00")

        # Mock the database import to raise ImportError when trying to import AsyncSessionLocal
        import builtins

        original_import = builtins.__import__

        def selective_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Only raise for the specific import we want to block
            if name == "app.db.database" and fromlist and "AsyncSessionLocal" in fromlist:
                raise ImportError("No DB")
            return original_import(name, globals, locals, fromlist, level)

        with patch.object(builtins, "__import__", side_effect=selective_import):
            # Act
            result = await estimate_cost(model_id, tokens_in, tokens_out, session=None)

            # Assert
            # Check that values are rounded
            assert len(str(result["input_cost"]).split(".")[-1]) <= 6
            assert len(str(result["output_cost"]).split(".")[-1]) <= 6
            assert len(str(result["total_cost"]).split(".")[-1]) <= 6

    @pytest.mark.asyncio
    async def test_multiple_models_env_default_consistency(self, monkeypatch):
        """Different model IDs use the same env defaults when DB is absent."""
        # Arrange
        monkeypatch.setenv("PRICING_DEFAULT_INPUT_PER_MILLION", "1.10")
        monkeypatch.setenv("PRICING_DEFAULT_OUTPUT_PER_MILLION", "2.20")
        cases = [
            ("gpt-4o", 1_000_000, 1_000_000, 3.30),
            ("gpt-4o-mini", 500_000, 500_000, 1.65),
            ("llama-3.1-70b", 250_000, 750_000, 2.2 * 0.75 + 1.1 * 0.25),
        ]

        # Act & Assert
        for mid, tin, tout, expected in cases:
            res = await estimate_cost(mid, tin, tout)
            assert res["currency"] == "EUR"
            assert res["total_cost"] == pytest.approx(expected, rel=1e-6)
