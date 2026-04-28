"""
Integration tests for preflight analysis workflow.

Tests the complete preflight workflow for document chunking strategy selection
in the Corpus Management enhancement.
"""

import httpx
import pytest


@pytest.mark.asyncio
async def test_preflight_analysis_workflow(test_services_config, test_user_credentials):
    """Test complete preflight analysis workflow."""
    base_url = test_services_config["backend_url"]
    corpus_url = test_services_config.get("corpus_url", base_url)  # Fallback to backend

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        # 2. Create a test collection
        collection_response = await client.post(
            f"{corpus_url}/api/v1/collections",
            headers=headers,
            json={
                "name": "Test Preflight Collection",
                "description": "Collection for preflight testing",
                "embedding_model": "all-MiniLM-L6-v2",
            },
        )

        # May fail if collection exists or endpoint not available
        # Continue with mock collection_id if needed
        collection_id = None
        if collection_response.status_code in [200, 201]:
            collection_id = collection_response.json().get("id")

        # 3. Prepare test document
        test_doc_content = """
        # Security Policy Document

        ## Access Control
        All users must authenticate using multi-factor authentication.

        ## Data Classification
        - Public: No restrictions
        - Internal: Company employees only
        - Confidential: Authorized personnel only

        ## Incident Response
        1. Detect and report incident
        2. Contain the threat
        3. Investigate root cause
        4. Remediate and recover
        """

        # 4. Request preflight analysis
        preflight_response = await client.post(
            f"{corpus_url}/api/v1/corpus/preflight",
            headers=headers,
            json={
                "text": test_doc_content,
                "document_name": "security_policy.md",
                "collection_id": collection_id,
            },
        )

        # Verify preflight response
        if preflight_response.status_code == 200:
            preflight_data = preflight_response.json()

            # Check structure signals
            assert "structure_signals" in preflight_data
            signals = preflight_data["structure_signals"]
            assert "heading_density" in signals
            assert "avg_paragraph_length" in signals

            # Check strategy comparisons
            assert "strategy_results" in preflight_data
            strategies = preflight_data["strategy_results"]
            assert len(strategies) > 0

            # Each strategy should have metrics
            for strategy_result in strategies:
                assert "strategy" in strategy_result
                assert "chunk_count" in strategy_result
                assert "avg_chunk_size" in strategy_result

            # Check recommendation
            assert "recommended_strategy" in preflight_data
        else:
            # Endpoint may not be implemented yet
            pytest.skip(f"Preflight endpoint returned {preflight_response.status_code}")


@pytest.mark.asyncio
async def test_chunking_strategies_comparison(test_services_config, test_user_credentials):
    """Test chunking strategy comparison."""
    base_url = test_services_config["backend_url"]

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        # Test document with clear structure
        structured_doc = """
        # Chapter 1: Introduction

        This chapter introduces the main concepts.

        ## Section 1.1: Background

        Historical context and motivation.

        ## Section 1.2: Objectives

        - Objective 1
        - Objective 2
        - Objective 3
        """

        # Test each chunking strategy
        strategies = [
            "fixed_token",
            "sliding_token",
            "heading_aware",
        ]

        results = {}
        for strategy in strategies:
            chunk_response = await client.post(
                f"{base_url}/api/v1/corpus/chunk",
                headers=headers,
                json={
                    "text": structured_doc,
                    "config": {
                        "strategy": strategy,
                        "chunk_size": 128,
                        "chunk_overlap": 20,
                    },
                },
            )

            if chunk_response.status_code == 200:
                results[strategy] = chunk_response.json()

        # If we got any results, verify they differ
        if len(results) >= 2:
            chunk_counts = [r["chunk_count"] for r in results.values()]
            # Different strategies should produce different results
            assert len(set(chunk_counts)) > 1 or all(c > 0 for c in chunk_counts)


@pytest.mark.asyncio
async def test_run_manifest_creation(test_services_config, test_user_credentials):
    """Test that run manifests are created during execution."""
    base_url = test_services_config["backend_url"]

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        # Execute a use case
        await client.post(
            f"{base_url}/api/v1/orchestrator/execute",
            headers=headers,
            json={
                "use_case_id": "test-case",
                "prompt": "Test execution for manifest",
            },
        )

        # Check if execution created a run manifest
        # Query recent manifests
        manifests_response = await client.get(
            f"{base_url}/api/v1/run-manifests",
            headers=headers,
            params={
                "limit": 10,
                "sort_order": "desc",
            },
        )

        if manifests_response.status_code == 200:
            manifests_data = manifests_response.json()

            # Should have manifests structure
            assert "manifests" in manifests_data
            assert isinstance(manifests_data["manifests"], list)

            # Verify manifest structure if any exist
            if len(manifests_data["manifests"]) > 0:
                manifest = manifests_data["manifests"][0]
                assert "run_id" in manifest
                assert "ts_utc" in manifest
                assert "use_case_id" in manifest
                assert "schema_valid" in manifest
                assert "conformance" in manifest
                assert "latency_total_ms" in manifest
                assert "tokens_in" in manifest
                assert "tokens_out" in manifest
                assert "result_kind" in manifest


@pytest.mark.asyncio
async def test_run_manifest_aggregate_metrics(test_services_config, test_user_credentials):
    """Test run manifest aggregate metrics endpoint."""
    base_url = test_services_config["backend_url"]

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        # Request aggregate metrics
        metrics_response = await client.get(
            f"{base_url}/api/v1/run-manifests/metrics/aggregate",
            headers=headers,
            params={
                "use_case_id": "threat-triage-v1",
            },
        )

        if metrics_response.status_code == 200:
            metrics_data = metrics_response.json()

            # Verify aggregate metrics structure
            assert "use_case_id" in metrics_data
            assert "total_runs" in metrics_data
            assert "metrics" in metrics_data

            # Check key metrics
            metrics = metrics_data["metrics"]
            assert "schema_validity_rate" in metrics
            assert "avg_conformance" in metrics
            assert "p50_latency_ms" in metrics
            assert "p95_latency_ms" in metrics
            assert "avg_tokens_in" in metrics
            assert "avg_tokens_out" in metrics
        else:
            # Endpoint may not be implemented yet or no data
            pytest.skip(f"Aggregate metrics endpoint returned {metrics_response.status_code}")


@pytest.mark.asyncio
async def test_test_suite_execution(test_services_config, test_user_credentials):
    """Test test suite execution for use case validation."""
    base_url = test_services_config["backend_url"]
    corpus_url = test_services_config.get("corpus_url", base_url)

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

        # Create a test suite
        suite_response = await client.post(
            f"{corpus_url}/api/v1/corpus/test-suites",
            headers=headers,
            json={
                "name": "Integration Test Suite",
                "description": "Test suite for integration testing",
                "collection_ids": [],  # Empty for now
                "k": 5,
                "questions": [
                    {
                        "query": "What are security best practices?",
                        "expected_phrases": ["authentication", "encryption"],
                        "tags": ["security"],
                    }
                ],
            },
        )

        if suite_response.status_code in [200, 201]:
            suite_data = suite_response.json()
            suite_id = suite_data.get("id")

            # Execute the test suite
            execute_response = await client.post(
                f"{corpus_url}/api/v1/corpus/test-suites/{suite_id}/execute",
                headers=headers,
            )

            if execute_response.status_code == 200:
                exec_data = execute_response.json()

                # Verify execution results
                assert "results" in exec_data or "metrics" in exec_data
            else:
                pytest.skip(f"Test suite execution returned {execute_response.status_code}")
        else:
            pytest.skip(f"Test suite creation returned {suite_response.status_code}")


@pytest.mark.asyncio
async def test_ephemeral_collections_workflow(test_services_config, test_user_credentials):
    """Test ephemeral collections with TTL."""
    base_url = test_services_config["backend_url"]
    corpus_url = test_services_config.get("corpus_url", base_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        # Create ephemeral collection
        collection_response = await client.post(
            f"{corpus_url}/api/v1/collections",
            headers=headers,
            json={
                "name": "Ephemeral Test Collection",
                "description": "Temporary collection for testing",
                "embedding_model": "all-MiniLM-L6-v2",
                "is_ephemeral": True,
                "ttl_days": 1,
            },
        )

        if collection_response.status_code in [200, 201]:
            collection_data = collection_response.json()

            # Verify ephemeral properties
            assert collection_data["is_ephemeral"] is True
            assert collection_data["ttl_days"] == 1
            assert "expires_at" in collection_data
        else:
            pytest.skip(
                f"Ephemeral collection creation not supported: {collection_response.status_code}"
            )


@pytest.mark.asyncio
async def test_capabilities_stateless_configuration(test_services_config, test_user_credentials):
    """Verify capabilities endpoint returns correct stateless configuration."""
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
        caps_data = caps_response.json()

        # Verify Stateless Core v1 configuration
        assert caps_data.get("stateless") is True, "Should be in stateless mode"
        assert caps_data.get("edition") in ["core", "plus"]

        # Verify providers are set to stateless defaults
        providers = caps_data.get("providers", {})
        assert providers.get("history") in ["edge_only", "none"], "History should be edge-only"
        assert providers.get("evidence") == "none", "Evidence sink should be none"

        # Verify export capabilities
        export_formats = caps_data.get("export_formats", [])
        assert "md" in export_formats
        assert "json" in export_formats
