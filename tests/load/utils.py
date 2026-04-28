"""
Utility functions for load testing.

Provides common functionality for load test scripts.
"""

import json
import os
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# JWT creation (reuse from conftest pattern)
try:
    import jwt as pyjwt  # PyJWT library
except ImportError:
    import jose.jwt as pyjwt  # type: ignore[no-redef]  # python-jose as fallback


@dataclass
class LatencyStats:
    """Latency statistics."""

    min: int = 0
    max: int = 0
    mean: float = 0.0
    median: int = 0
    p50: int = 0
    p95: int = 0
    p99: int = 0
    stdev: float = 0.0


def create_test_token(
    user_id: str = "load_test_user",
    role: str = "user",
    scopes: list[str] | None = None,
) -> str:
    """
    Create a test JWT token with specified scopes.

    Uses real admin token from orchestrator if available (recommended).
    Falls back to generating test token if orchestrator unavailable.

    Args:
        user_id: User ID for the token
        role: User role
        scopes: List of scopes (e.g., ["inference:chat"])

    Returns:
        JWT token string
    """
    # Try to get real admin token from orchestrator (preferred)
    auth_token = os.environ.get("AUTH_TOKEN")
    if auth_token:
        return auth_token

    # Try to fetch from orchestrator
    try:
        import httpx

        response = httpx.post(
            "http://localhost:8006/auth/token",
            data={
                "username": "admin",
                "password": "adminpassword",
            },
            timeout=5.0,
        )
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            return data["access_token"]
    except Exception:
        pass  # Fall back to generating test token

    # Generate test token (may not work if JWT_SECRET doesn't match)
    if scopes is None:
        scopes = []

    # Get JWT config from environment (match conftest.py defaults)
    secret = os.environ.get("JWT_SECRET", "test_secret_key_minimum_32_chars_long_for_security")
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    issuer = os.environ.get("JWT_ISSUER", "test-gateway")  # Match conftest.py default

    now = datetime.now()
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "scopes": scopes,
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": issuer,
        "token_type": "access",
    }

    return pyjwt.encode(payload, secret, algorithm=algorithm)


def calculate_percentiles(latencies: list[int]) -> LatencyStats:
    """
    Calculate latency statistics from list of latencies in milliseconds.

    Args:
        latencies: List of latency values in milliseconds

    Returns:
        LatencyStats with percentiles and statistics
    """
    if not latencies:
        return LatencyStats()

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def percentile(p: float) -> int:
        """Calculate percentile value."""
        idx = int(n * p)
        if idx >= n:
            idx = n - 1
        return sorted_latencies[idx]

    return LatencyStats(
        min=min(sorted_latencies),
        max=max(sorted_latencies),
        mean=statistics.mean(sorted_latencies),
        median=int(statistics.median(sorted_latencies)),
        p50=percentile(0.50),
        p95=percentile(0.95),
        p99=percentile(0.99),
        stdev=statistics.stdev(sorted_latencies) if len(sorted_latencies) > 1 else 0.0,
    )


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1m 23s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.1f}s"


def print_results(results: Any, config: Any) -> None:
    """
    Print load test results to console.

    Args:
        results: LoadTestResults object
        config: LoadTestConfig object
    """
    stats = results.get_latency_stats()

    print(f"Duration:          {format_duration(results.duration_seconds)}")
    print(f"Target RPS:        {config.rps:.2f} ({config.rps * 60:.0f} req/min)")
    print(f"Actual RPS:        {results.actual_rps:.2f} ({results.actual_rps * 60:.0f} req/min)")
    print()

    print("Requests:")
    print(f"  Total:           {results.total_requests}")
    print(f"  Successful:      {results.successful_requests}")
    print(f"  Failed:          {results.failed_requests}")
    print(f"  Rate Limited:    {results.rate_limited_requests}")
    print(f"  Success Rate:    {results.success_rate:.2f}%")
    print()

    if results.latencies_ms:
        print("Latency (ms):")
        print(f"  Min:             {stats.min}")
        print(f"  Max:             {stats.max}")
        print(f"  Mean:            {stats.mean:.1f}")
        print(f"  Median:          {stats.median}")
        print(f"  p50:             {stats.p50}")
        print(f"  p95:             {stats.p95}")
        print(f"  p99:             {stats.p99}")
        print(f"  StdDev:          {stats.stdev:.1f}")
        print()

    if results.errors:
        print("Errors:")
        for error_type, count in sorted(results.errors.items(), key=lambda x: -x[1]):
            print(f"  {error_type}: {count}")
        print()


def write_results_json(results: Any, config: Any, output_path: str) -> None:
    """
    Write load test results to JSON file.

    Args:
        results: LoadTestResults object
        config: LoadTestConfig object
        output_path: Path to output JSON file
    """
    stats = results.get_latency_stats()

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "gateway_url": config.gateway_url,
            "rps": config.rps,
            "duration": config.duration,
            "model": config.model,
            "max_concurrent": config.max_concurrent,
            "timeout": config.timeout,
        },
        "results": {
            "total_requests": results.total_requests,
            "successful_requests": results.successful_requests,
            "failed_requests": results.failed_requests,
            "rate_limited_requests": results.rate_limited_requests,
            "success_rate": results.success_rate,
            "actual_rps": results.actual_rps,
            "duration_seconds": results.duration_seconds,
        },
        "latency_ms": {
            "min": stats.min,
            "max": stats.max,
            "mean": stats.mean,
            "median": stats.median,
            "p50": stats.p50,
            "p95": stats.p95,
            "p99": stats.p99,
            "stdev": stats.stdev,
        },
        "errors": results.errors,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
