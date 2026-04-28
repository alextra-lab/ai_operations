"""Use case validation test harness.

This module provides a framework for executing use case validation tests
against run manifests to ensure quality metrics meet defined SLOs.

Supports:
- YAML-based test suite definitions
- N-run execution for statistical validity
- Aggregate metric computation (SVR, conformance, tool stability)
- JUnit XML report generation
- Run manifest telemetry validation

Usage:
    python ops/testing/use_case_harness.py test_suites/uc_threat_triage.yaml
    python ops/testing/use_case_harness.py --suite-dir tests/fixtures/use_case_suites/
"""

import asyncio
import hashlib
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backend.app.schemas.run_manifest import RunManifest

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Individual test case within a suite."""

    name: str
    use_case_id: str
    input_prompt: str
    context_refs: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    min_conformance: float = 0.95
    max_latency_ms: int = 5000


@dataclass
class TestSuite:
    """Test suite specification."""

    id: str
    name: str
    description: str
    n_runs: int
    expect: dict[str, float]
    cases: list[TestCase]

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "TestSuite":
        """Parse test suite from YAML file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        cases = [
            TestCase(
                name=case["name"],
                use_case_id=case["use_case_id"],
                input_prompt=case["input_prompt"],
                context_refs=case.get("context_refs", []),
                expected_tools=case.get("expected_tools", []),
                min_conformance=case.get("min_conformance", 0.95),
                max_latency_ms=case.get("max_latency_ms", 5000),
            )
            for case in data["cases"]
        ]

        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            n_runs=data.get("n_runs", 10),
            expect=data["expect"],
            cases=cases,
        )


@dataclass
class CaseResult:
    """Results for a single test case execution."""

    case_name: str
    run_id: UUID
    schema_valid: bool
    conformance: float
    tool_chain: list[str]
    latency_total_ms: int
    latency_llm_ms: int
    tokens_in: int
    tokens_out: int
    result_kind: str
    idempotence_ok: bool


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple runs."""

    svr: float  # Schema Validity Rate
    avg_conformance: float
    tool_selection_stability: float
    p50_latency: int
    p95_latency: int
    p99_latency: int
    avg_tokens_in: float
    avg_tokens_out: float
    idempotence_violations: int


@dataclass
class TestResult:
    """Complete test suite result."""

    suite_id: str
    suite_name: str
    execution_time: datetime
    total_runs: int
    case_results: list[CaseResult]
    aggregate_metrics: AggregateMetrics
    passed: bool
    failures: list[str] = field(default_factory=list)


class UseCaseHarness:
    """Execute use case validation tests against run manifests."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8006",
        db_connection_string: str | None = None,
    ):
        """Initialize harness.

        Args:
            api_base_url: Base URL for backend API
            db_connection_string: PostgreSQL connection string for run manifest queries
        """
        self.api_base_url = api_base_url
        self.db_connection_string = db_connection_string or (
            "postgresql://testuser:testpass@localhost:5434/aio-test"
        )

    async def run_suite(self, suite_path: Path) -> TestResult:
        """Execute test suite.

        Args:
            suite_path: Path to YAML test suite file

        Returns:
            TestResult with aggregated metrics and pass/fail status
        """
        logger.info(f"Loading test suite: {suite_path}")
        suite = TestSuite.from_yaml(suite_path)

        logger.info(
            f"Executing suite '{suite.name}' with {len(suite.cases)} cases, "
            f"{suite.n_runs} runs per case"
        )

        case_results = []
        datetime.utcnow()

        for case in suite.cases:
            logger.info(f"Running case: {case.name} ({suite.n_runs} iterations)")
            for run_idx in range(suite.n_runs):
                result = await self._run_case(case, run_idx + 1)
                case_results.append(result)

        # Compute aggregate metrics
        aggregate = self._compute_aggregate_metrics(case_results)

        # Validate against SLOs
        failures = self._validate_slos(suite, aggregate)
        passed = len(failures) == 0

        execution_time = datetime.utcnow()

        return TestResult(
            suite_id=suite.id,
            suite_name=suite.name,
            execution_time=execution_time,
            total_runs=len(case_results),
            case_results=case_results,
            aggregate_metrics=aggregate,
            passed=passed,
            failures=failures,
        )

    async def _run_case(self, case: TestCase, run_number: int) -> CaseResult:
        """Execute a single test case.

        Args:
            case: Test case specification
            run_number: Run iteration number

        Returns:
            CaseResult with execution metrics
        """
        import httpx

        run_id = uuid4()

        # Execute use case via API
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/orchestrator/execute",
                    json={
                        "use_case_id": case.use_case_id,
                        "prompt": case.input_prompt,
                        "context_refs": case.context_refs,
                        "run_id": str(run_id),
                    },
                )
                response.raise_for_status()
                response.json()

                # Wait for run manifest to be written
                await asyncio.sleep(0.5)

                # Fetch run manifest from database
                manifest = await self._fetch_run_manifest(run_id)

                if manifest:
                    return CaseResult(
                        case_name=case.name,
                        run_id=run_id,
                        schema_valid=manifest.schema_valid,
                        conformance=manifest.conformance,
                        tool_chain=manifest.tool_chain,
                        latency_total_ms=manifest.latency_total_ms,
                        latency_llm_ms=manifest.latency_llm_ms,
                        tokens_in=manifest.tokens_in,
                        tokens_out=manifest.tokens_out,
                        result_kind=manifest.result_kind,
                        idempotence_ok=manifest.idempotence_ok,
                    )

                logger.warning(f"No run manifest found for run_id: {run_id}")
                # Return synthetic failure result
                return self._create_failure_result(case, run_id, "no_manifest")

            except Exception as e:
                logger.error(f"Case execution failed: {e}")
                return self._create_failure_result(case, run_id, f"error: {e}")

    def _create_failure_result(
        self,
        case: TestCase,
        run_id: UUID,
        reason: str,
    ) -> CaseResult:
        """Create a failure result for a test case."""
        return CaseResult(
            case_name=case.name,
            run_id=run_id,
            schema_valid=False,
            conformance=0.0,
            tool_chain=[],
            latency_total_ms=0,
            latency_llm_ms=0,
            tokens_in=0,
            tokens_out=0,
            result_kind="error",
            idempotence_ok=False,
        )

    async def _fetch_run_manifest(self, run_id: UUID) -> RunManifest | None:
        """Fetch run manifest from database.

        Args:
            run_id: Run ID to fetch

        Returns:
            RunManifest if found, None otherwise
        """
        try:
            import asyncpg

            conn = await asyncpg.connect(self.db_connection_string)
            try:
                row = await conn.fetchrow(
                    """
                    SELECT
                        run_id, ts_utc, use_case_id, template_ver, model_name,
                        model_version, params_hash, schema_valid, conformance,
                        tool_chain, idempotence_ok, latency_total_ms,
                        latency_llm_ms, latency_tools_ms, tokens_in, tokens_out,
                        result_kind
                    FROM run_manifests
                    WHERE run_id = $1
                    """,
                    run_id,
                )

                if row:
                    return RunManifest(**dict(row))
                return None
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch run manifest: {e}")
            return None

    def _compute_aggregate_metrics(self, case_results: list[CaseResult]) -> AggregateMetrics:
        """Compute aggregated metrics across all case results.

        Args:
            case_results: List of all case execution results

        Returns:
            AggregateMetrics with computed values
        """
        if not case_results:
            return AggregateMetrics(
                svr=0.0,
                avg_conformance=0.0,
                tool_selection_stability=0.0,
                p50_latency=0,
                p95_latency=0,
                p99_latency=0,
                avg_tokens_in=0.0,
                avg_tokens_out=0.0,
                idempotence_violations=0,
            )

        # Schema Validity Rate
        svr = sum(1 for r in case_results if r.schema_valid) / len(case_results)

        # Average conformance
        avg_conformance = sum(r.conformance for r in case_results) / len(case_results)

        # Tool selection stability (percentage of runs with same tool chain hash)
        tool_chain_hashes = [
            hashlib.md5("".join(r.tool_chain).encode()).hexdigest() for r in case_results
        ]
        most_common_hash = max(set(tool_chain_hashes), key=tool_chain_hashes.count)
        tool_selection_stability = tool_chain_hashes.count(most_common_hash) / len(
            tool_chain_hashes
        )

        # Latency percentiles
        latencies = sorted([r.latency_total_ms for r in case_results])
        p50_latency = latencies[int(len(latencies) * 0.50)]
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]

        # Token usage
        avg_tokens_in = sum(r.tokens_in for r in case_results) / len(case_results)
        avg_tokens_out = sum(r.tokens_out for r in case_results) / len(case_results)

        # Idempotence violations
        idempotence_violations = sum(1 for r in case_results if not r.idempotence_ok)

        return AggregateMetrics(
            svr=svr,
            avg_conformance=avg_conformance,
            tool_selection_stability=tool_selection_stability,
            p50_latency=p50_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            avg_tokens_in=avg_tokens_in,
            avg_tokens_out=avg_tokens_out,
            idempotence_violations=idempotence_violations,
        )

    def _validate_slos(self, suite: TestSuite, metrics: AggregateMetrics) -> list[str]:
        """Validate aggregate metrics against SLO expectations.

        Args:
            suite: Test suite with expected SLOs
            metrics: Computed aggregate metrics

        Returns:
            List of failure messages (empty if all passed)
        """
        failures = []

        # Check Schema Validity Rate
        if "svr_min" in suite.expect and metrics.svr < suite.expect["svr_min"]:
            failures.append(f"SVR {metrics.svr:.3f} < threshold {suite.expect['svr_min']:.3f}")

        # Check conformance
        if (
            "conformance_min" in suite.expect
            and metrics.avg_conformance < suite.expect["conformance_min"]
        ):
            failures.append(
                f"Conformance {metrics.avg_conformance:.3f} < threshold "
                f"{suite.expect['conformance_min']:.3f}"
            )

        # Check tool selection stability
        if (
            "tool_stability_min" in suite.expect
            and metrics.tool_selection_stability < suite.expect["tool_stability_min"]
        ):
            failures.append(
                f"Tool stability {metrics.tool_selection_stability:.3f} < threshold "
                f"{suite.expect['tool_stability_min']:.3f}"
            )

        # Check p95 latency
        if (
            "p95_latency_max" in suite.expect
            and metrics.p95_latency > suite.expect["p95_latency_max"]
        ):
            failures.append(
                f"p95 latency {metrics.p95_latency}ms > threshold "
                f"{suite.expect['p95_latency_max']}ms"
            )

        # Check idempotence
        if (
            "idempotence_violations_max" in suite.expect
            and metrics.idempotence_violations > suite.expect["idempotence_violations_max"]
        ):
            failures.append(
                f"Idempotence violations {metrics.idempotence_violations} > threshold "
                f"{suite.expect['idempotence_violations_max']}"
            )

        return failures

    def generate_junit_xml(self, result: TestResult, output_path: Path) -> None:
        """Generate JUnit XML report.

        Args:
            result: Test result to convert
            output_path: Path to write XML file
        """
        from xml.etree.ElementTree import Element, ElementTree, SubElement

        testsuite = Element(
            "testsuite",
            name=result.suite_name,
            tests=str(len(result.case_results)),
            failures=str(len(result.failures)),
            time=str((datetime.utcnow() - result.execution_time).total_seconds()),
        )

        # Add properties
        properties = SubElement(testsuite, "properties")
        SubElement(properties, "property", name="svr", value=f"{result.aggregate_metrics.svr:.3f}")
        SubElement(
            properties,
            "property",
            name="avg_conformance",
            value=f"{result.aggregate_metrics.avg_conformance:.3f}",
        )
        SubElement(
            properties,
            "property",
            name="tool_stability",
            value=f"{result.aggregate_metrics.tool_selection_stability:.3f}",
        )
        SubElement(
            properties,
            "property",
            name="p95_latency",
            value=str(result.aggregate_metrics.p95_latency),
        )

        # Add test cases
        for case_result in result.case_results:
            testcase = SubElement(
                testsuite,
                "testcase",
                name=case_result.case_name,
                classname=result.suite_id,
                time=str(case_result.latency_total_ms / 1000.0),
            )

            if not case_result.schema_valid or case_result.conformance < 0.95:
                failure = SubElement(testcase, "failure", message="Quality metrics below threshold")
                failure.text = (
                    f"schema_valid={case_result.schema_valid}, "
                    f"conformance={case_result.conformance:.3f}"
                )

        tree = ElementTree(testsuite)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        logger.info(f"JUnit XML report written to: {output_path}")

    def print_summary(self, result: TestResult) -> None:
        """Print human-readable test summary.

        Args:
            result: Test result to summarize
        """
        print("\n" + "=" * 80)
        print(f"Test Suite: {result.suite_name}")
        print("=" * 80)
        print(f"Total Runs: {result.total_runs}")
        print(f"Execution Time: {result.execution_time}")
        print()
        print("Aggregate Metrics:")
        print(f"  SVR (Schema Validity Rate):    {result.aggregate_metrics.svr:.3f}")
        print(f"  Average Conformance:            {result.aggregate_metrics.avg_conformance:.3f}")
        print(
            f"  Tool Selection Stability:       {result.aggregate_metrics.tool_selection_stability:.3f}"
        )
        print(f"  p50 Latency:                    {result.aggregate_metrics.p50_latency} ms")
        print(f"  p95 Latency:                    {result.aggregate_metrics.p95_latency} ms")
        print(f"  p99 Latency:                    {result.aggregate_metrics.p99_latency} ms")
        print(f"  Avg Tokens In:                  {result.aggregate_metrics.avg_tokens_in:.1f}")
        print(f"  Avg Tokens Out:                 {result.aggregate_metrics.avg_tokens_out:.1f}")
        print(
            f"  Idempotence Violations:         {result.aggregate_metrics.idempotence_violations}"
        )
        print()

        if result.passed:
            print("✅ PASSED - All SLOs met")
        else:
            print("❌ FAILED - SLO violations:")
            for failure in result.failures:
                print(f"  - {failure}")
        print("=" * 80 + "\n")


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Use case validation test harness")
    parser.add_argument("suite_path", type=Path, help="Path to YAML test suite file")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8006",
        help="Backend API base URL (default: http://localhost:8006)",
    )
    parser.add_argument(
        "--db-connection",
        help="PostgreSQL connection string (default: test database)",
    )
    parser.add_argument(
        "--junit-xml",
        type=Path,
        help="Path to write JUnit XML report",
    )

    args = parser.parse_args()

    if not args.suite_path.exists():
        print(f"Error: Suite file not found: {args.suite_path}")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Run harness
    harness = UseCaseHarness(
        api_base_url=args.api_url,
        db_connection_string=args.db_connection,
    )

    result = await harness.run_suite(args.suite_path)

    # Print summary
    harness.print_summary(result)

    # Generate JUnit XML if requested
    if args.junit_xml:
        harness.generate_junit_xml(result, args.junit_xml)

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
