"""Capture a golden baseline from a running ``llm-guard-svc``.

Run this against the *current* (llm-guard-backed) service to snapshot the
behaviour the migration must preserve, then commit the JSON under ``golden/``.
The current service only runs inside its Docker image (the host cannot import
``llm-guard``), so capture talks to it over HTTP.

Usage::

    python -m src.llm_guard_svc.tests.parity.capture \
        --url http://localhost:18081 \
        --latency-reps 15

Outputs (next to this file, under ``golden/``):
    * ``baseline.json``  — one full response payload per corpus case + provenance
    * ``latency.json``   — p50/p95/p99/max latency across the latency reps
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from .client import health, validate
from .corpus import CORPUS, case_ids

GOLDEN_DIR = Path(__file__).parent / "golden"


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (no interpolation; deterministic, stdlib-only)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, round((pct / 100.0) * len(ordered)))
    return round(ordered[min(rank, len(ordered)) - 1], 3)


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def capture(url: str, latency_reps: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture functional responses + latency stats. Returns (baseline, latency)."""
    case_ids()  # validate no duplicate ids before we start

    if not health(url):
        raise SystemExit(f"service at {url} is not healthy; bring up llm-guard-svc first")

    responses: dict[str, Any] = {}
    all_latencies: list[float] = []
    per_case_latency: dict[str, float] = {}

    for case in CORPUS:
        probe = validate(url, case)
        if probe.status != 200:
            raise SystemExit(f"case {case.id!r} returned HTTP {probe.status}: {probe.payload}")
        responses[case.id] = {
            "category": case.category,
            "target_scanner": case.target_scanner,
            "input_text": case.text,
            "response": probe.payload,
        }
        per_case_latency[case.id] = round(probe.latency_ms, 3)

    # Latency pass: repeated probes over the whole corpus for a stable p99.
    for _ in range(latency_reps):
        for case in CORPUS:
            probe = validate(url, case)
            all_latencies.append(probe.latency_ms)

    baseline = {
        "_provenance": {
            "source_url": url,
            "git_head": _git_head(),
            "case_count": len(CORPUS),
            "note": "Golden baseline from the current llm-guard-backed service (LLG-04 §5).",
        },
        "cases": responses,
    }
    latency = {
        "_provenance": {
            "source_url": url,
            "git_head": _git_head(),
            "latency_reps": latency_reps,
            "sample_count": len(all_latencies),
        },
        "warm_single_pass_ms": per_case_latency,
        "aggregate_ms": {
            "p50": _percentile(all_latencies, 50),
            "p95": _percentile(all_latencies, 95),
            "p99": _percentile(all_latencies, 99),
            "max": round(max(all_latencies), 3) if all_latencies else 0.0,
        },
    }
    return baseline, latency


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture LLG-04 golden baseline.")
    parser.add_argument(
        "--url",
        default="http://localhost:18081",
        help="Base URL of the running current service (default: %(default)s).",
    )
    parser.add_argument(
        "--latency-reps",
        type=int,
        default=15,
        help="Repeats over the full corpus for latency stats (default: %(default)s).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=GOLDEN_DIR,
        help="Directory to write baseline.json / latency.json (default: golden/).",
    )
    args = parser.parse_args()

    baseline, latency = capture(args.url, args.latency_reps)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "baseline.json").write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False) + "\n"
    )
    (args.out_dir / "latency.json").write_text(
        json.dumps(latency, indent=2, ensure_ascii=False) + "\n"
    )

    agg = latency["aggregate_ms"]
    print(f"Wrote {len(baseline['cases'])} cases -> {args.out_dir / 'baseline.json'}")
    print(f"Latency p50={agg['p50']}ms p95={agg['p95']}ms p99={agg['p99']}ms max={agg['max']}ms")


if __name__ == "__main__":
    main()
