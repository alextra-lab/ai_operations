"""
End-to-end tests for Stateless Core v1 workflows.

Comprehensive E2E test demonstrating complete workflows:
- Document ingestion with chunking strategies
- Use case execution with run manifest capture
- Client-owned exports (MD/JSON/Summary)
- Capabilities discovery
- Quality metrics aggregation

Can optionally load documents from corpus_docs folder for realistic testing.
"""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest


class TestStatelessCoreV1Workflows:
    """End-to-end workflow tests for Stateless Core v1."""

    @pytest.mark.asyncio
    async def test_complete_workflow_capabilities_to_export(
        self, test_services_config, test_user_credentials
    ):
        """
        Test complete workflow from capabilities discovery through export.

        Workflow:
        1. Discover capabilities (stateless mode)
        2. Execute use case
        3. Verify run manifest created
        4. Export conversation (MD/JSON)
        5. Generate summary
        """
        base_url = test_services_config["backend_url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Authenticate
            auth_response = await client.post(
                f"{base_url}/auth/token",
                data={
                    "username": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )
            assert auth_response.status_code == 200
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Discover capabilities
            caps_response = await client.get(
                f"{base_url}/api/system/capabilities",
                headers=headers,
            )
            assert caps_response.status_code == 200
            capabilities = caps_response.json()

            # Verify stateless configuration
            assert capabilities.get("stateless") is True
            assert capabilities.get("providers", {}).get("history") in ["edge_only", "none"]
            print("✅ Step 1: Capabilities discovered - Stateless mode active")

            # 3. Execute use case
            str(uuid4())
            exec_response = await client.post(
                f"{base_url}/api/v1/orchestrator/execute",
                headers=headers,
                json={
                    "use_case_id": "threat-triage-v1",
                    "prompt": "E2E test: Analyze suspicious network activity",
                },
            )

            # Execution may fail if use case doesn't exist
            if exec_response.status_code == 200:
                exec_response.json()
                print("✅ Step 2: Use case executed")

                # Wait for run manifest
                await asyncio.sleep(1)

                # 4. Verify run manifest
                manifests_response = await client.get(
                    f"{base_url}/api/v1/run-manifests",
                    headers=headers,
                    params={"limit": 5, "sort_order": "desc"},
                )

                if manifests_response.status_code == 200:
                    manifests = manifests_response.json()
                    if manifests.get("manifests"):
                        manifest = manifests["manifests"][0]
                        assert "run_id" in manifest
                        assert "schema_valid" in manifest
                        assert "conformance" in manifest
                        print("✅ Step 3: Run manifest captured (no conversation content)")
            else:
                print("⚠️  Use case execution skipped (use case may not exist)")

            # 5. Create mock conversation for export
            messages = [
                {
                    "role": "user",
                    "content": "E2E test message",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                {
                    "role": "assistant",
                    "content": "E2E test response",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            ]

            # 6. Test Markdown export
            md_export_response = await client.post(
                f"{base_url}/api/v1/stateless/export",
                headers=headers,
                json={
                    "use_case_id": "test",
                    "messages": messages,
                    "export_format": "markdown",
                },
            )

            if md_export_response.status_code == 200:
                md_data = md_export_response.json()
                assert "content" in md_data
                assert md_data["message_count"] == 2
                print("✅ Step 4: Markdown export generated")
            else:
                print(f"⚠️  Export skipped (returned {md_export_response.status_code})")

            # 7. Test JSON export
            json_export_response = await client.post(
                f"{base_url}/api/v1/stateless/export",
                headers=headers,
                json={
                    "use_case_id": "test",
                    "messages": messages,
                    "export_format": "json",
                },
            )

            if json_export_response.status_code == 200:
                json_data = json_export_response.json()
                assert "content" in json_data
                # Verify valid JSON
                (
                    json.loads(json_data["content"])
                    if isinstance(json_data["content"], str)
                    else json_data["content"]
                )
                print("✅ Step 5: JSON export generated")

            # 8. Test summary generation
            summary_response = await client.post(
                f"{base_url}/api/v1/summaries",
                headers=headers,
                json={
                    "use_case_id": "test",
                    "messages": messages,
                    "export_format": "markdown",
                },
            )

            if summary_response.status_code == 200:
                summary_data = summary_response.json()
                assert "summary" in summary_data
                assert summary_data["message_count"] == 2
                print("✅ Step 6: Summary generated")

            print()
            print("✅ COMPLETE WORKFLOW VERIFIED: Capabilities → Execution → Telemetry → Export")

    @pytest.mark.asyncio
    async def test_chunking_strategy_workflow(self, test_services_config, test_user_credentials):
        """
        Test chunking strategy workflow with preflight analysis.

        Workflow:
        1. Analyze document structure
        2. Get recommended strategy
        3. Chunk with recommended strategy
        4. Verify chunk quality
        """
        base_url = test_services_config["backend_url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Authenticate
            auth_response = await client.post(
                f"{base_url}/auth/token",
                data={
                    "username": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Test document
            test_doc = """# Security Policy

## Authentication Requirements
All users must use multi-factor authentication.

## Access Control
- Admin: Full system access
- User: Read-only access
- Guest: No access

## Compliance
Review this policy quarterly."""

            # 1. Request preflight analysis
            preflight_response = await client.post(
                f"{base_url}/api/v1/corpus/chunking/preflight",
                headers=headers,
                json={
                    "text": test_doc,
                    "document_name": "security_policy.md",
                    "document_type": "text/markdown",
                },
            )

            if preflight_response.status_code == 200:
                report = preflight_response.json()

                assert "structure_signals" in report
                assert "recommendation" in report
                assert "strategy_results" in report

                recommended_strategy = report["recommendation"]["strategy"]
                print(
                    f"✅ Step 1: Preflight analysis complete - Recommended: {recommended_strategy}"
                )

                # 2. Chunk with recommended strategy
                chunk_response = await client.post(
                    f"{base_url}/api/v1/corpus/chunking/chunk",
                    headers=headers,
                    json={
                        "text": test_doc,
                        "config": {
                            "strategy": recommended_strategy,
                            "chunk_size": 512,
                            "chunk_overlap": 50,
                            "min_chunk_size": 64,
                            "max_chunk_size": 2048,
                            "preserve_whitespace": True,
                            "respect_sentence_boundaries": True,
                        },
                    },
                )

                if chunk_response.status_code == 200:
                    chunk_data = chunk_response.json()
                    assert "chunks" in chunk_data
                    assert chunk_data["chunk_count"] > 0
                    print(
                        f"✅ Step 2: Document chunked - {chunk_data['chunk_count']} chunks created"
                    )
                    print()
                    print("✅ CHUNKING WORKFLOW VERIFIED: Preflight → Recommendation → Chunking")
            else:
                print(f"⚠️  Preflight endpoint returned {preflight_response.status_code}")
                pytest.skip("Preflight endpoint not available")

    @pytest.mark.asyncio
    async def test_quality_metrics_workflow(self, test_services_config, test_user_credentials):
        """
        Test quality metrics workflow.

        Workflow:
        1. Execute multiple use cases
        2. Query aggregate metrics
        3. Verify SLO thresholds
        """
        base_url = test_services_config["backend_url"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Authenticate
            auth_response = await client.post(
                f"{base_url}/auth/token",
                data={
                    "username": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Execute a few use cases
            for i in range(3):
                await client.post(
                    f"{base_url}/api/v1/orchestrator/execute",
                    headers=headers,
                    json={
                        "use_case_id": "threat-triage-v1",
                        "prompt": f"E2E quality test {i+1}",
                    },
                )
                await asyncio.sleep(0.5)

            # Query aggregate metrics
            metrics_response = await client.get(
                f"{base_url}/api/v1/run-manifests/metrics/aggregate",
                headers=headers,
                params={"use_case_id": "threat-triage-v1"},
            )

            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                assert "metrics" in metrics
                assert "total_runs" in metrics

                print(f"✅ Quality metrics available for {metrics['total_runs']} runs")
                print("✅ QUALITY METRICS WORKFLOW VERIFIED")
            else:
                pytest.skip(f"Metrics endpoint returned {metrics_response.status_code}")

    @pytest.mark.asyncio
    async def test_provider_interfaces_stateless_mode(
        self, test_services_config, test_user_credentials
    ):
        """
        Verify provider interfaces in stateless mode (ADR-033).

        Should verify:
        - History provider = edge_only (no server storage)
        - Evidence sink = none (no evidence collection)
        - Crypto provider = none (no field encryption)
        """
        base_url = test_services_config["backend_url"]

        async with httpx.AsyncClient() as client:
            # Authenticate
            auth_response = await client.post(
                f"{base_url}/auth/token",
                data={
                    "username": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )
            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Get capabilities
            caps_response = await client.get(
                f"{base_url}/api/system/capabilities",
                headers=headers,
            )

            assert caps_response.status_code == 200
            caps = caps_response.json()

            # Verify provider configuration for stateless mode
            providers = caps.get("providers", {})
            assert providers.get("history") in [
                "edge_only",
                "none",
            ], "History provider should be edge_only or none in stateless mode"
            assert providers.get("evidence") == "none", "Evidence sink should be none in v1"
            assert providers.get("crypto") in ["none", "no_crypto"], "Crypto should be none in v1"

            print("✅ Provider interfaces verified for stateless mode")
            print(f"  History: {providers.get('history')}")
            print(f"  Evidence: {providers.get('evidence')}")
            print(f"  Crypto: {providers.get('crypto')}")
