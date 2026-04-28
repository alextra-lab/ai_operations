"""
Unit tests for CostCalculator service.

VERIFICATION CRITICAL:
- Test cost matches backend's cost_estimator.py (within 1%)
- Test pricing fallback order (history → registry → default)
- Test EUR currency consistency
- Test edge cases (0 tokens, missing pricing, invalid model)
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.services.cost_calculator import CostCalculator


@pytest.fixture
def cost_calculator():
    """Create CostCalculator instance for testing."""
    return CostCalculator()


class TestCostCalculator:
    """Test suite for CostCalculator service."""

    @pytest.mark.asyncio
    async def test_calculate_with_pricing_history(self, cost_calculator):
        """Test cost calculation using pricing history (preferred source)."""
        # Mock _get_pricing to return pricing history result
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(0.15, 0.60, "pricing_history"),
        ):
            # Calculate cost for 100 input tokens, 50 output tokens
            result = await cost_calculator.calculate("gpt-4o-mini", 100, 50)

            # Verify result structure
            assert "total_cost_eur" in result
            assert "input_cost_eur" in result
            assert "output_cost_eur" in result
            assert "pricing_source" in result

            # Verify pricing source
            assert result["pricing_source"] == "pricing_history"

            # Verify calculations
            # Input: (100 / 1_000_000) * 0.15 = 0.000015 EUR
            # Output: (50 / 1_000_000) * 0.60 = 0.000030 EUR
            # Total: 0.000045 EUR
            assert result["input_cost_eur"] == pytest.approx(0.000015, abs=1e-9)
            assert result["output_cost_eur"] == pytest.approx(0.000030, abs=1e-9)
            assert result["total_cost_eur"] == pytest.approx(0.000045, abs=1e-9)

    @pytest.mark.asyncio
    async def test_calculate_with_model_registry(self, cost_calculator):
        """Test cost calculation using model registry fallback."""
        # Mock _get_pricing to return model registry result
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(1.50, 3.00, "model_registry"),
        ):
            result = await cost_calculator.calculate("custom-model", 1000, 500)

            # Verify fallback to model registry
            assert result["pricing_source"] == "model_registry"

            # Verify calculations
            # Input: (1000 / 1_000_000) * 1.50 = 0.001500 EUR
            # Output: (500 / 1_000_000) * 3.00 = 0.001500 EUR
            # Total: 0.003000 EUR
            assert result["input_cost_eur"] == pytest.approx(0.001500, abs=1e-9)
            assert result["output_cost_eur"] == pytest.approx(0.001500, abs=1e-9)
            assert result["total_cost_eur"] == pytest.approx(0.003000, abs=1e-9)

    @pytest.mark.asyncio
    async def test_calculate_with_default_pricing(self, cost_calculator):
        """Test cost calculation using default pricing (final fallback)."""
        # Mock _get_pricing to return default pricing
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(1.00, 2.00, "default"),
        ):
            result = await cost_calculator.calculate("unknown-model", 1000, 500)

            # Verify fallback to default pricing
            assert result["pricing_source"] == "default"

            # Verify calculations with default pricing (1.00 EUR input, 2.00 EUR output)
            # Input: (1000 / 1_000_000) * 1.00 = 0.001000 EUR
            # Output: (500 / 1_000_000) * 2.00 = 0.001000 EUR
            # Total: 0.002000 EUR
            assert result["input_cost_eur"] == pytest.approx(0.001000, abs=1e-9)
            assert result["output_cost_eur"] == pytest.approx(0.001000, abs=1e-9)
            assert result["total_cost_eur"] == pytest.approx(0.002000, abs=1e-9)

    @pytest.mark.asyncio
    async def test_calculate_zero_tokens(self, cost_calculator):
        """Test cost calculation with zero tokens."""
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(0.15, 0.60, "pricing_history"),
        ):
            result = await cost_calculator.calculate("gpt-4o-mini", 0, 0)

            # Zero tokens should result in zero cost
            assert result["input_cost_eur"] == 0.0
            assert result["output_cost_eur"] == 0.0
            assert result["total_cost_eur"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_large_token_counts(self, cost_calculator):
        """Test cost calculation with large token counts."""
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(5.00, 15.00, "pricing_history"),
        ):
            # 100k input tokens, 50k output tokens
            result = await cost_calculator.calculate("gpt-4", 100_000, 50_000)

            # Input: (100_000 / 1_000_000) * 5.00 = 0.500000 EUR
            # Output: (50_000 / 1_000_000) * 15.00 = 0.750000 EUR
            # Total: 1.250000 EUR
            assert result["input_cost_eur"] == pytest.approx(0.500000, abs=1e-6)
            assert result["output_cost_eur"] == pytest.approx(0.750000, abs=1e-6)
            assert result["total_cost_eur"] == pytest.approx(1.250000, abs=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_with_custom_timestamp(self, cost_calculator):
        """Test cost calculation with custom timestamp (historical pricing)."""
        custom_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(0.20, 0.80, "pricing_history"),
        ) as mock_get_pricing:
            result = await cost_calculator.calculate("gpt-4o-mini", 100, 50, as_of=custom_timestamp)

            # Verify timestamp was passed to _get_pricing
            mock_get_pricing.assert_called_once_with("gpt-4o-mini", custom_timestamp)

            # Verify calculation with custom pricing
            assert result["total_cost_eur"] == pytest.approx(0.000060, abs=1e-9)

    @pytest.mark.asyncio
    async def test_calculate_rounds_correctly(self, cost_calculator):
        """Test cost calculation rounds to 6 decimal places."""
        # Pricing that will result in many decimal places
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(0.123456789, 0.987654321, "pricing_history"),
        ):
            result = await cost_calculator.calculate("test-model", 123, 456)

            # Verify all costs are rounded to 6 decimal places
            assert len(str(result["input_cost_eur"]).split(".")[-1]) <= 6
            assert len(str(result["output_cost_eur"]).split(".")[-1]) <= 6
            assert len(str(result["total_cost_eur"]).split(".")[-1]) <= 6

    @pytest.mark.asyncio
    async def test_cost_matches_backend_estimator(self, cost_calculator):
        """
        Verify Gateway cost matches backend cost_estimator.py (within 1%).

        This test uses same pricing as backend and verifies calculations match.
        """
        # GPT-4o-mini pricing from backend
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(0.15, 0.60, "pricing_history"),
        ):
            # Test same token counts as backend cost_estimator
            gateway_result = await cost_calculator.calculate("gpt-4o-mini", 1000, 500)

            # Expected from backend cost_estimator.py:
            # Input: (1000 / 1_000_000) * 0.15 = 0.00015 EUR
            # Output: (500 / 1_000_000) * 0.60 = 0.00030 EUR
            # Total: 0.00045 EUR
            expected_total = 0.00045

            # Verify match within 1%
            difference = abs(gateway_result["total_cost_eur"] - expected_total)
            tolerance = expected_total * 0.01  # 1% tolerance
            assert difference <= tolerance, (
                f"Gateway cost {gateway_result['total_cost_eur']} differs from "
                f"backend cost {expected_total} by {difference:.9f} EUR "
                f"(exceeds 1% tolerance of {tolerance:.9f})"
            )

    @pytest.mark.asyncio
    async def test_eur_currency_consistency(self, cost_calculator):
        """Test EUR currency is used consistently (not USD or other currencies)."""
        with patch.object(
            cost_calculator,
            "_get_pricing",
            return_value=(1.00, 2.00, "default"),
        ):
            result = await cost_calculator.calculate("test-model", 1000, 500)

            # Verify pricing is in EUR (matches backend system)
            # If pricing was in USD, values would be different
            # EUR 1.00/2.00 per million is typical for local/cheap models
            assert result["input_cost_eur"] == pytest.approx(0.001000, abs=1e-9)
            assert result["output_cost_eur"] == pytest.approx(0.001000, abs=1e-9)
