#!/usr/bin/env python3
"""
Performance benchmarks for async database operations.

P5-A21: Validates async database migration performance (ADR-022).

Tests:
- Direct database operations (connection pool, queries, transactions)
- API endpoints that use database (end-to-end)
- Concurrent request handling
- Connection pool utilization

Usage:
    python tests/benchmarks/benchmark_async_db.py
    python tests/benchmarks/benchmark_async_db.py --iterations 100 --concurrency 10
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# Add benchmarks directory to path for local imports
benchmark_dir = Path(__file__).parent
sys.path.insert(0, str(benchmark_dir))

# Import benchmark utilities
from benchmark_utils import (
    BenchmarkStats,
    format_stats_json,
    print_benchmark_stats,
    run_concurrent_benchmarks,
)

from shared.auth.models import User
from src.orchestrator.app.db.database import AsyncSessionLocal, init_db
from src.orchestrator.app.db.models import UseCase


async def benchmark_simple_query(db: AsyncSession) -> None:
    """Benchmark simple SELECT query."""
    result = await db.execute(select(User).limit(1))
    result.scalar_one_or_none()


async def benchmark_count_query(db: AsyncSession) -> None:
    """Benchmark COUNT query."""
    result = await db.execute(select(func.count()).select_from(UseCase))
    result.scalar_one()


async def benchmark_filtered_query(db: AsyncSession) -> None:
    """Benchmark filtered query with WHERE clause."""
    result = await db.execute(select(UseCase).where(UseCase.is_active.is_(True)).limit(10))
    result.scalars().all()


async def benchmark_join_query(db: AsyncSession) -> None:
    """Benchmark query with JOIN."""
    from src.orchestrator.app.db.models import UserUseCaseAssignment

    result = await db.execute(
        select(UseCase, UserUseCaseAssignment)
        .join(UserUseCaseAssignment, UseCase.id == UserUseCaseAssignment.use_case_id)
        .limit(10)
    )
    result.all()


async def benchmark_transaction(db: AsyncSession) -> None:
    """Benchmark transaction (read + write)."""
    # Read
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if user:
        # Write (update)
        user.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)


async def benchmark_api_endpoint(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    json_data: dict | None = None,
) -> None:
    """Benchmark API endpoint call."""
    if method.upper() == "GET":
        response = await client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
    elif method.upper() == "POST":
        response = await client.post(url, headers=headers, json=json_data, timeout=30.0)
        response.raise_for_status()
    else:
        raise ValueError(f"Unsupported method: {method}")


async def run_database_benchmarks(
    iterations: int,
    concurrency: int,
) -> dict[str, BenchmarkStats]:
    """Run benchmarks for direct database operations."""
    print(f"\n{'=' * 60}")
    print("Direct Database Operation Benchmarks")
    print(f"{'=' * 60}")

    await init_db()

    benchmarks = {
        "simple_query": benchmark_simple_query,
        "count_query": benchmark_count_query,
        "filtered_query": benchmark_filtered_query,
        "join_query": benchmark_join_query,
        "transaction": benchmark_transaction,
    }

    results: dict[str, BenchmarkStats] = {}

    for name, benchmark_func in benchmarks.items():
        print(f"\nRunning {name} benchmark...")

        # Capture loop variables to avoid closure issues
        captured_func = benchmark_func

        async def run_with_session() -> None:
            async with AsyncSessionLocal() as session:
                await captured_func(session)

        start_time = time.perf_counter()
        benchmark_results = await run_concurrent_benchmarks(
            name,
            run_with_session,
            concurrency,
            iterations,
        )
        end_time = time.perf_counter()

        stats = BenchmarkStats.from_results(
            name,
            benchmark_results,
            end_time - start_time,
        )
        results[name] = stats
        print_benchmark_stats(stats)

    return results


async def run_api_benchmarks(
    orchestrator_url: str,
    token: str,
    iterations: int,
    concurrency: int,
) -> dict[str, BenchmarkStats]:
    """Run benchmarks for API endpoints."""
    print(f"\n{'=' * 60}")
    print("API Endpoint Benchmarks (End-to-End)")
    print(f"{'=' * 60}")

    headers = {"Authorization": f"Bearer {token}"}

    # Define API endpoints to benchmark
    api_benchmarks = {
        "get_use_cases": {
            "method": "GET",
            "url": f"{orchestrator_url}/api/v1/use-cases/available",
            "headers": headers,
        },
        "get_tools": {
            "method": "GET",
            "url": f"{orchestrator_url}/api/v1/tools/available",
            "headers": headers,
        },
        "get_query_history": {
            "method": "GET",
            "url": f"{orchestrator_url}/api/v1/query-history?limit=10",
            "headers": headers,
        },
    }

    results: dict[str, BenchmarkStats] = {}

    async with httpx.AsyncClient() as client:
        for name, config in api_benchmarks.items():
            print(f"\nRunning {name} benchmark...")

            # Capture loop variables to avoid closure issues
            captured_config = config

            async def run_api_call() -> None:
                method: str = (
                    captured_config["method"]
                    if isinstance(captured_config["method"], str)
                    else str(captured_config["method"])
                )
                url: str = (
                    captured_config["url"]
                    if isinstance(captured_config["url"], str)
                    else str(captured_config["url"])
                )
                headers = captured_config.get("headers")
                json_data = captured_config.get("json_data")
                await benchmark_api_endpoint(
                    client,
                    method,
                    url,
                    headers if isinstance(headers, dict) else None,
                    json_data if isinstance(json_data, dict) else None,
                )

            start_time = time.perf_counter()
            benchmark_results = await run_concurrent_benchmarks(
                name,
                run_api_call,
                concurrency,
                iterations,
            )
            end_time = time.perf_counter()

            stats = BenchmarkStats.from_results(
                name,
                benchmark_results,
                end_time - start_time,
            )
            results[name] = stats
            print_benchmark_stats(stats)

    return results


async def get_auth_token(orchestrator_url: str) -> str:
    """Get authentication token for API benchmarks."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{orchestrator_url}/auth/token",
            data={
                "username": os.environ.get("TEST_USERNAME", "admin"),
                "password": os.environ.get("TEST_PASSWORD", "adminpassword"),
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data["access_token"]


async def main() -> None:
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Async database performance benchmarks")
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of iterations per benchmark (default: 50)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Concurrent operations (default: 10)",
    )
    parser.add_argument(
        "--orchestrator-url",
        type=str,
        default="http://localhost:8006",
        help="Orchestrator API URL (default: http://localhost:8006)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (default: results/benchmark_YYYYMMDD_HHMMSS.json)",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip API endpoint benchmarks",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip direct database benchmarks",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("P5-A21: Async Database Performance Benchmarks")
    print("=" * 60)
    print(f"Iterations: {args.iterations}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Orchestrator URL: {args.orchestrator_url}")

    all_results: dict[str, dict[str, BenchmarkStats]] = {}

    # Run database benchmarks
    if not args.skip_db:
        db_results = await run_database_benchmarks(args.iterations, args.concurrency)
        all_results["database"] = db_results

    # Run API benchmarks
    if not args.skip_api:
        try:
            token = await get_auth_token(args.orchestrator_url)
            api_results = await run_api_benchmarks(
                args.orchestrator_url,
                token,
                args.iterations,
                args.concurrency,
            )
            all_results["api"] = api_results
        except (httpx.HTTPError, httpx.RequestError, KeyError, ValueError) as e:
            print(f"\n⚠️  Warning: Could not run API benchmarks: {type(e).__name__}")
            print("   Make sure orchestrator is running and credentials are correct.")

    # Format results for JSON output
    json_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "iterations": args.iterations,
            "concurrency": args.concurrency,
            "orchestrator_url": args.orchestrator_url,
        },
        "results": {
            category: {name: format_stats_json(stats) for name, stats in category_results.items()}
            for category, category_results in all_results.items()
        },
    }

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = results_dir / f"benchmark_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Benchmark Summary")
    print("=" * 60)

    for category, category_results in all_results.items():
        print(f"\n{category.upper()}:")
        for name, stats in category_results.items():
            print(
                f"  {name:30s} p95: {stats.p95_latency_ms:6.2f}ms  "
                f"ops/sec: {stats.operations_per_second:6.2f}  "
                f"success: {stats.success_rate:5.1f}%"
            )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
