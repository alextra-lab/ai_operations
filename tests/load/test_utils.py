"""
Unit tests for load test utility functions.

Tests token generation, statistics calculation, and formatting functions.
"""

import json
import sys
from pathlib import Path

# Add load test directory to path
load_dir = Path(__file__).parent
sys.path.insert(0, str(load_dir))

from utils import (
    LatencyStats,
    calculate_percentiles,
    create_test_token,
    format_duration,
    write_results_json,
)


class TestTokenGeneration:
    """Tests for JWT token generation."""

    def test_create_test_token_default(self):
        """Test creating token with defaults."""
        token = create_test_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # Should have 3 parts (header.payload.signature)
        assert token.count(".") == 2

    def test_create_test_token_custom_user(self):
        """Test creating token with custom user."""
        token = create_test_token(user_id="custom_user", role="admin")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_test_token_with_scopes(self):
        """Test creating token with scopes."""
        token = create_test_token(scopes=["inference:chat", "inference:embeddings"])
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_env_token_override(self, monkeypatch):
        """Test that AUTH_TOKEN env var overrides generation."""
        expected_token = "override_token_from_env"
        monkeypatch.setenv("AUTH_TOKEN", expected_token)

        token = create_test_token()
        assert token == expected_token


class TestLatencyStatistics:
    """Tests for latency statistics calculation."""

    def test_calculate_percentiles_empty(self):
        """Test with empty latency list."""
        stats = calculate_percentiles([])
        assert stats.min == 0
        assert stats.max == 0
        assert stats.mean == 0.0
        assert stats.p50 == 0
        assert stats.p95 == 0
        assert stats.p99 == 0

    def test_calculate_percentiles_single_value(self):
        """Test with single value."""
        stats = calculate_percentiles([100])
        assert stats.min == 100
        assert stats.max == 100
        assert stats.mean == 100.0
        assert stats.median == 100
        assert stats.p50 == 100
        assert stats.p95 == 100
        assert stats.p99 == 100
        assert stats.stdev == 0.0

    def test_calculate_percentiles_multiple_values(self):
        """Test with multiple values."""
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        stats = calculate_percentiles(latencies)

        assert stats.min == 10
        assert stats.max == 100
        assert stats.mean == 55.0
        assert stats.median == 55
        # Percentile calculation uses index-based method
        assert stats.p50 in [50, 60]  # 50th percentile (index-based)
        assert stats.p95 in [95, 100]  # 95th percentile
        assert stats.p99 in [99, 100]  # 99th percentile
        assert stats.stdev > 0  # Should have some variation

    def test_calculate_percentiles_realistic_data(self):
        """Test with realistic Gateway latency data."""
        # Simulate 100 requests with realistic latency distribution
        latencies = (
            [50] * 10  # Fast requests
            + [100] * 30  # Most requests
            + [150] * 40  # Average requests
            + [200] * 15  # Slower requests
            + [500] * 5  # Outliers
        )

        stats = calculate_percentiles(latencies)

        assert stats.min == 50
        assert stats.max == 500
        assert 100 < stats.mean < 200  # Average should be reasonable
        assert stats.p50 <= stats.p95  # p95 should be >= median
        assert stats.p95 <= stats.p99  # p99 should be >= p95


class TestFormatting:
    """Tests for formatting functions."""

    def test_format_duration_seconds(self):
        """Test formatting durations under 1 minute."""
        assert format_duration(0.5) == "0.5s"
        assert format_duration(15.3) == "15.3s"
        assert format_duration(59.9) == "59.9s"

    def test_format_duration_minutes(self):
        """Test formatting durations over 1 minute."""
        assert format_duration(60.0) == "1m 0.0s"
        assert format_duration(90.5) == "1m 30.5s"
        assert format_duration(125.3) == "2m 5.3s"
        assert format_duration(3661.0) == "61m 1.0s"


class TestResultsIO:
    """Tests for results I/O functions."""

    def test_write_results_json(self, tmp_path):
        """Test writing results to JSON file."""
        from dataclasses import dataclass

        @dataclass
        class MockConfig:
            gateway_url: str = "http://test"
            rps: float = 5.0
            duration: int = 10
            model: str = "test-model"
            max_concurrent: int = 50
            timeout: int = 30

        @dataclass
        class MockResults:
            total_requests: int = 100
            successful_requests: int = 95
            failed_requests: int = 5
            rate_limited_requests: int = 0
            success_rate: float = 95.0
            actual_rps: float = 4.9
            duration_seconds: float = 10.2
            errors: dict = None
            latencies_ms: list = None

            def __post_init__(self):
                if self.errors is None:
                    self.errors = {}
                if self.latencies_ms is None:
                    self.latencies_ms = [100, 150, 200]

            def get_latency_stats(self):
                return calculate_percentiles(self.latencies_ms)

        config = MockConfig()
        results = MockResults()

        output_file = tmp_path / "test_results.json"
        write_results_json(results, config, str(output_file))

        # Verify file was created
        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "config" in data
        assert "results" in data
        assert "latency_ms" in data
        assert data["config"]["rps"] == 5.0
        assert data["results"]["total_requests"] == 100
        assert data["results"]["success_rate"] == 95.0
        assert "p50" in data["latency_ms"]
        assert "p95" in data["latency_ms"]


class TestLatencyStatsDataclass:
    """Tests for LatencyStats dataclass."""

    def test_latency_stats_creation(self):
        """Test creating LatencyStats object."""
        stats = LatencyStats(
            min=10, max=100, mean=50.5, median=50, p50=50, p95=95, p99=99, stdev=15.2
        )

        assert stats.min == 10
        assert stats.max == 100
        assert stats.mean == 50.5
        assert stats.median == 50
        assert stats.p50 == 50
        assert stats.p95 == 95
        assert stats.p99 == 99
        assert stats.stdev == 15.2

    def test_latency_stats_defaults(self):
        """Test LatencyStats with default values."""
        stats = LatencyStats()

        assert stats.min == 0
        assert stats.max == 0
        assert stats.mean == 0.0
        assert stats.p50 == 0
        assert stats.p95 == 0
        assert stats.p99 == 0
