"""
Timing Tracker Utility for Performance Monitoring.

This module provides utilities for tracking execution times of different
pipeline components (retrieval, guard, model) to enable performance analysis.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class TimingTracker:
    """
    Tracks execution times for different pipeline components.

    Usage:
        tracker = TimingTracker()

        with tracker.track("retrieval"):
            # ... retrieval code ...
            pass

        with tracker.track("guard"):
            # ... guard code ...
            pass

        with tracker.track("model"):
            # ... model code ...
            pass

        metrics = tracker.get_metrics()
        # Returns: {
        #     "retrieval_time": 0.123,
        #     "guard_time": 0.045,
        #     "model_time": 2.456,
        #     "total_time": 2.624,
        #     "breakdown": {
        #         "retrieval_pct": 4.7,
        #         "guard_pct": 1.7,
        #         "model_pct": 93.6
        #     }
        # }
    """

    def __init__(self) -> None:
        """Initialize timing tracker."""
        self._start_time: float | None = None
        self._timings: dict[str, float] = {}
        self._component_starts: dict[str, float] = {}

    def start(self) -> None:
        """Start overall timing."""
        self._start_time = time.time()

    @contextmanager
    def track(self, component: str) -> Iterator[None]:
        """
        Context manager for tracking component execution time.

        Args:
            component: Name of the component being timed

        Yields:
            None

        Example:
            with tracker.track("retrieval"):
                # retrieval code here
                pass
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self._timings[component] = elapsed

    def record(self, component: str, duration: float) -> None:
        """
        Manually record a timing for a component.

        Args:
            component: Name of the component
            duration: Duration in seconds
        """
        self._timings[component] = duration

    def get_timing(self, component: str) -> float | None:
        """
        Get timing for a specific component.

        Args:
            component: Name of the component

        Returns:
            Duration in seconds, or None if not tracked
        """
        return self._timings.get(component)

    def get_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive timing metrics with breakdown.

        Returns:
            Dictionary containing:
            - Individual component times
            - Total time
            - Percentage breakdown
        """
        total = sum(self._timings.values())

        breakdown: dict[str, float] = {}
        # Calculate percentage breakdown
        if total > 0:
            breakdown = {
                "retrieval_pct": round((self._timings.get("retrieval", 0.0) / total) * 100, 1),
                "guard_pct": round((self._timings.get("guard", 0.0) / total) * 100, 1),
                "model_pct": round((self._timings.get("model", 0.0) / total) * 100, 1),
            }
        else:
            breakdown = {
                "retrieval_pct": 0.0,
                "guard_pct": 0.0,
                "model_pct": 0.0,
            }

        metrics: dict[str, Any] = {
            # Individual timings
            "retrieval_time": self._timings.get("retrieval", 0.0),
            "guard_time": self._timings.get("guard", 0.0),
            "model_time": self._timings.get("model", 0.0),
            "total_time": total,
            "breakdown": breakdown,
        }

        return metrics

    def get_total_time(self) -> float:
        """
        Get total elapsed time since start().

        Returns:
            Total time in seconds
        """
        if self._start_time is None:
            return sum(self._timings.values())
        return time.time() - self._start_time

    def reset(self) -> None:
        """Reset all timings."""
        self._start_time = None
        self._timings.clear()
        self._component_starts.clear()


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "123.4ms", "2.5s", "1m 30s")
    """
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.1f}µs"
    if seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"
