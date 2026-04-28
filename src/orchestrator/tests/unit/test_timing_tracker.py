"""
Unit tests for timing_tracker utility.

Tests timing tracking functionality for pipeline components.
"""

import time

import pytest

from src.orchestrator.app.utils.timing_tracker import TimingTracker, format_duration


class TestTimingTracker:
    """Test suite for timing tracker utility."""

    def test_timing_tracker_initialization(self):
        """Test that timing tracker initializes properly."""
        # Arrange & Act
        tracker = TimingTracker()

        # Assert
        assert tracker._start_time is None
        assert len(tracker._timings) == 0

    def test_track_single_component(self):
        """Test tracking a single component."""
        # Arrange
        tracker = TimingTracker()

        # Act
        with tracker.track("test_component"):
            time.sleep(0.1)  # Sleep for 100ms

        # Assert
        timing = tracker.get_timing("test_component")
        assert timing is not None
        assert timing >= 0.1
        assert timing < 0.2  # Should be less than 200ms

    def test_track_multiple_components(self):
        """Test tracking multiple components."""
        # Arrange
        tracker = TimingTracker()

        # Act
        with tracker.track("retrieval"):
            time.sleep(0.05)

        with tracker.track("guard"):
            time.sleep(0.02)

        with tracker.track("model"):
            time.sleep(0.10)

        # Assert
        retrieval_time = tracker.get_timing("retrieval")
        guard_time = tracker.get_timing("guard")
        model_time = tracker.get_timing("model")

        assert retrieval_time >= 0.05
        assert guard_time >= 0.02
        assert model_time >= 0.10

    def test_get_timing_nonexistent_component(self):
        """Test getting timing for non-existent component returns None."""
        # Arrange
        tracker = TimingTracker()

        # Act
        timing = tracker.get_timing("nonexistent")

        # Assert
        assert timing is None

    def test_record_manual_timing(self):
        """Test manually recording a timing."""
        # Arrange
        tracker = TimingTracker()

        # Act
        tracker.record("manual_component", 1.5)

        # Assert
        timing = tracker.get_timing("manual_component")
        assert timing == 1.5

    def test_get_metrics_structure(self):
        """Test that get_metrics returns proper structure."""
        # Arrange
        tracker = TimingTracker()
        with tracker.track("retrieval"):
            time.sleep(0.01)
        with tracker.track("guard"):
            time.sleep(0.01)
        with tracker.track("model"):
            time.sleep(0.01)

        # Act
        metrics = tracker.get_metrics()

        # Assert
        assert "retrieval_time" in metrics
        assert "guard_time" in metrics
        assert "model_time" in metrics
        assert "total_time" in metrics
        assert "breakdown" in metrics
        assert "retrieval_pct" in metrics["breakdown"]
        assert "guard_pct" in metrics["breakdown"]
        assert "model_pct" in metrics["breakdown"]

    def test_get_metrics_percentage_calculation(self):
        """Test that percentage breakdown is calculated correctly."""
        # Arrange
        tracker = TimingTracker()
        tracker.record("retrieval", 0.1)  # 10%
        tracker.record("guard", 0.2)  # 20%
        tracker.record("model", 0.7)  # 70%

        # Act
        metrics = tracker.get_metrics()

        # Assert
        assert metrics["total_time"] == 1.0
        assert metrics["breakdown"]["retrieval_pct"] == pytest.approx(10.0, rel=0.1)
        assert metrics["breakdown"]["guard_pct"] == pytest.approx(20.0, rel=0.1)
        assert metrics["breakdown"]["model_pct"] == pytest.approx(70.0, rel=0.1)

    def test_get_metrics_zero_total(self):
        """Test metrics when no timings have been recorded."""
        # Arrange
        tracker = TimingTracker()

        # Act
        metrics = tracker.get_metrics()

        # Assert
        assert metrics["total_time"] == 0.0
        assert metrics["breakdown"]["retrieval_pct"] == 0.0
        assert metrics["breakdown"]["guard_pct"] == 0.0
        assert metrics["breakdown"]["model_pct"] == 0.0

    def test_start_and_get_total_time(self):
        """Test start() and get_total_time() methods."""
        # Arrange
        tracker = TimingTracker()

        # Act
        tracker.start()
        time.sleep(0.05)
        total_time = tracker.get_total_time()

        # Assert
        assert total_time >= 0.05
        assert total_time < 0.1

    def test_reset(self):
        """Test that reset clears all timings."""
        # Arrange
        tracker = TimingTracker()
        tracker.start()
        with tracker.track("test"):
            time.sleep(0.01)

        # Act
        tracker.reset()

        # Assert
        assert tracker._start_time is None
        assert len(tracker._timings) == 0
        assert tracker.get_timing("test") is None

    def test_track_context_manager_exception(self):
        """Test that timing is recorded even if exception occurs."""
        # Arrange
        tracker = TimingTracker()

        # Act & Assert
        with pytest.raises(ValueError), tracker.track("error_component"):
            time.sleep(0.01)
            raise ValueError("Test error")

        # Timing should still be recorded
        timing = tracker.get_timing("error_component")
        assert timing is not None
        assert timing >= 0.01

    def test_overwrite_timing(self):
        """Test that re-tracking a component overwrites previous timing."""
        # Arrange
        tracker = TimingTracker()

        # Act
        with tracker.track("component"):
            time.sleep(0.01)

        first_timing = tracker.get_timing("component")

        with tracker.track("component"):
            time.sleep(0.02)

        second_timing = tracker.get_timing("component")

        # Assert
        assert second_timing != first_timing
        assert second_timing > first_timing


class TestFormatDuration:
    """Test suite for duration formatting utility."""

    def test_format_duration_microseconds(self):
        """Test formatting durations less than 1ms."""
        # Arrange & Act
        result = format_duration(0.0001)  # 0.1ms = 100µs

        # Assert
        assert "µs" in result
        assert "100" in result

    def test_format_duration_milliseconds(self):
        """Test formatting durations in milliseconds."""
        # Arrange & Act
        result = format_duration(0.123)  # 123ms

        # Assert
        assert "ms" in result
        assert "123" in result

    def test_format_duration_seconds(self):
        """Test formatting durations in seconds."""
        # Arrange & Act
        result = format_duration(2.5)  # 2.5s

        # Assert
        assert "s" in result
        assert "2.5" in result

    def test_format_duration_minutes(self):
        """Test formatting durations in minutes."""
        # Arrange & Act
        result = format_duration(90.5)  # 1m 30.5s

        # Assert
        assert "m" in result
        assert "1m" in result
        assert "30" in result

    def test_format_duration_zero(self):
        """Test formatting zero duration."""
        # Arrange & Act
        result = format_duration(0.0)

        # Assert
        assert "µs" in result or "ms" in result

    @pytest.mark.parametrize(
        ("duration", "expected_unit"),
        [
            (0.0001, "µs"),
            (0.001, "ms"),
            (0.5, "ms"),
            (1.0, "s"),
            (30.0, "s"),
            (60.0, "m"),
            (120.0, "m"),
        ],
    )
    def test_format_duration_units(self, duration, expected_unit):
        """Test that correct units are used for various durations."""
        # Arrange & Act
        result = format_duration(duration)

        # Assert
        assert expected_unit in result


class TestTimingTrackerIntegration:
    """Integration tests for timing tracker in realistic scenarios."""

    def test_pipeline_simulation(self):
        """Test timing tracker in a simulated pipeline."""
        # Arrange
        tracker = TimingTracker()
        tracker.start()

        # Act - Simulate pipeline
        with tracker.track("retrieval"):
            time.sleep(0.05)

        with tracker.track("guard"):
            time.sleep(0.02)

        with tracker.track("model"):
            time.sleep(0.10)

        # Assert
        metrics = tracker.get_metrics()

        # Total time should be approximately sum of components
        assert metrics["total_time"] >= 0.17
        assert metrics["total_time"] < 0.25

        # Model should take the largest percentage
        assert metrics["breakdown"]["model_pct"] > metrics["breakdown"]["retrieval_pct"]
        assert metrics["breakdown"]["model_pct"] > metrics["breakdown"]["guard_pct"]

        # All percentages should sum to approximately 100%
        total_pct = (
            metrics["breakdown"]["retrieval_pct"]
            + metrics["breakdown"]["guard_pct"]
            + metrics["breakdown"]["model_pct"]
        )
        assert total_pct == pytest.approx(100.0, rel=0.1)

    def test_nested_tracking_not_supported(self):
        """Test that nested tracking uses flat structure (overwrites)."""
        # Arrange
        tracker = TimingTracker()

        # Act
        with tracker.track("outer"):
            time.sleep(0.01)
            with tracker.track("inner"):
                time.sleep(0.01)

        # Assert
        # Both should have timings, but they're independent
        assert tracker.get_timing("outer") is not None
        assert tracker.get_timing("inner") is not None
