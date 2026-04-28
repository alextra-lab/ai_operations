"""
Utility functions for performance benchmarks.

P5-A21: Performance benchmarks for async database migration validation.
"""

import asyncio
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a single benchmark operation."""

    operation_name: str
    latency_ms: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkStats:
    """Aggregated statistics for a benchmark suite."""

    operation_name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    latencies_ms: list[float]
    min_latency_ms: float
    max_latency_ms: float
    mean_latency_ms: float
    median_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    std_dev_ms: float
    success_rate: float
    total_duration_seconds: float
    operations_per_second: float

    @classmethod
    def from_results(
        cls,
        operation_name: str,
        results: list[BenchmarkResult],
        total_duration_seconds: float,
    ) -> "BenchmarkStats":
        """Create stats from a list of benchmark results."""
        successful = [r for r in results if r.success]
        latencies = [r.latency_ms for r in successful]

        if not latencies:
            return cls(
                operation_name=operation_name,
                total_operations=len(results),
                successful_operations=0,
                failed_operations=len(results),
                latencies_ms=[],
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                mean_latency_ms=0.0,
                median_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                std_dev_ms=0.0,
                success_rate=0.0,
                total_duration_seconds=total_duration_seconds,
                operations_per_second=0.0,
            )

        sorted_latencies = sorted(latencies)

        def percentile(data: list[float], p: float) -> float:
            """Calculate percentile."""
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] + c * (data[f + 1] - data[f])
            return data[f]

        return cls(
            operation_name=operation_name,
            total_operations=len(results),
            successful_operations=len(successful),
            failed_operations=len(results) - len(successful),
            latencies_ms=sorted_latencies,
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            mean_latency_ms=statistics.mean(latencies),
            median_latency_ms=statistics.median(latencies),
            p50_latency_ms=percentile(sorted_latencies, 0.50),
            p95_latency_ms=percentile(sorted_latencies, 0.95),
            p99_latency_ms=percentile(sorted_latencies, 0.99),
            std_dev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            success_rate=len(successful) / len(results) * 100.0,
            total_duration_seconds=total_duration_seconds,
            operations_per_second=(
                len(successful) / total_duration_seconds if total_duration_seconds > 0 else 0.0
            ),
        )


async def run_single_benchmark(
    operation_name: str,
    operation: Callable[[], Any],
    *args: Any,
    **kwargs: Any,
) -> BenchmarkResult:
    """
    Run a single benchmark operation.

    Args:
        operation_name: Name of the operation being benchmarked
        operation: Async function to benchmark
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation

    Returns:
        BenchmarkResult with timing and success status
    """
    start_time = time.perf_counter()
    error = None
    success = False

    try:
        if asyncio.iscoroutinefunction(operation):
            await operation(*args, **kwargs)
        else:
            operation(*args, **kwargs)
        success = True
    except Exception as e:
        error = str(e)
        success = False

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000.0

    return BenchmarkResult(
        operation_name=operation_name,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )


async def run_concurrent_benchmarks(
    operation_name: str,
    operation: Callable[[], Any],
    concurrency: int,
    iterations: int,
    *args: Any,
    **kwargs: Any,
) -> list[BenchmarkResult]:
    """
    Run multiple benchmark operations concurrently.

    Args:
        operation_name: Name of the operation being benchmarked
        operation: Async function to benchmark
        concurrency: Number of concurrent operations
        iterations: Total number of operations to run
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation

    Returns:
        List of BenchmarkResult objects
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[BenchmarkResult] = []

    async def run_with_semaphore() -> BenchmarkResult:
        async with semaphore:
            return await run_single_benchmark(operation_name, operation, *args, **kwargs)

    tasks = [run_with_semaphore() for _ in range(iterations)]
    results = await asyncio.gather(*tasks)

    return list(results)


def print_benchmark_stats(stats: BenchmarkStats) -> None:
    """Print benchmark statistics in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"Benchmark: {stats.operation_name}")
    print(f"{'=' * 60}")
    print(f"Total Operations:     {stats.total_operations}")
    print(f"Successful:           {stats.successful_operations}")
    print(f"Failed:               {stats.failed_operations}")
    print(f"Success Rate:         {stats.success_rate:.2f}%")
    print("\nLatency Statistics (ms):")
    print(f"  Min:                {stats.min_latency_ms:.2f}")
    print(f"  Max:                {stats.max_latency_ms:.2f}")
    print(f"  Mean:               {stats.mean_latency_ms:.2f}")
    print(f"  Median:             {stats.median_latency_ms:.2f}")
    print(f"  Std Dev:            {stats.std_dev_ms:.2f}")
    print("\nPercentiles (ms):")
    print(f"  p50:                {stats.p50_latency_ms:.2f}")
    print(f"  p95:                {stats.p95_latency_ms:.2f}")
    print(f"  p99:                {stats.p99_latency_ms:.2f}")
    print("\nThroughput:")
    print(f"  Operations/sec:     {stats.operations_per_second:.2f}")
    print(f"  Total Duration:     {stats.total_duration_seconds:.2f}s")
    print(f"{'=' * 60}\n")


def format_stats_json(stats: BenchmarkStats) -> dict[str, Any]:
    """Format benchmark stats as JSON-serializable dict."""
    return {
        "operation_name": stats.operation_name,
        "total_operations": stats.total_operations,
        "successful_operations": stats.successful_operations,
        "failed_operations": stats.failed_operations,
        "success_rate": stats.success_rate,
        "latency_ms": {
            "min": stats.min_latency_ms,
            "max": stats.max_latency_ms,
            "mean": stats.mean_latency_ms,
            "median": stats.median_latency_ms,
            "std_dev": stats.std_dev_ms,
            "p50": stats.p50_latency_ms,
            "p95": stats.p95_latency_ms,
            "p99": stats.p99_latency_ms,
        },
        "throughput": {
            "operations_per_second": stats.operations_per_second,
            "total_duration_seconds": stats.total_duration_seconds,
        },
    }
