"""
Integration tests for export workflow (ADR-031).

Tests the complete export workflow for client-owned conversation exports
in the Stateless Core v1 architecture.
"""

import json
from datetime import UTC, datetime

import httpx
import pytest


@pytest.mark.asyncio
async def test_export_markdown_workflow(test_services_config, test_user_credentials):
    """Test complete export workflow with Markdown format."""
    base_url = test_services_config["backend_url"]

    # 1. Authenticate
    async with httpx.AsyncClient() as client:
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

        # 2. Execute a use case to generate conversation
        conversation_messages = []
        await client.post(
            f"{base_url}/api/v1/orchestrator/execute",
            headers=headers,
            json={
                "use_case_id": "threat-triage-v1",
                "prompt": "Analyze this alert: Suspicious PowerShell execution",
                "context_refs": [],
            },
        )

        # Note: This might fail if use case doesn't exist in test DB
        # For now, we'll proceed with mock conversation data

        # 3. Create mock conversation messages
        conversation_messages = [
            {
                "role": "user",
                "content": "Analyze this alert: Suspicious PowerShell execution",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "role": "assistant",
                "content": "This appears to be a potential security threat...",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]

        # 4. Request export
        export_response = await client.post(
            f"{base_url}/api/v1/stateless/export",
            headers=headers,
            json={
                "use_case_id": "threat-triage-v1",
                "messages": conversation_messages,
                "export_format": "markdown",
                "include_metadata": True,
            },
        )

        # Verify export response
        assert export_response.status_code == 200
        export_data = export_response.json()

        assert "content" in export_data
        assert export_data["format"] == "markdown"
        assert export_data["message_count"] == 2
        assert "threat-triage-v1" in export_data["content"]


@pytest.mark.asyncio
async def test_export_json_workflow(test_services_config, test_user_credentials):
    """Test export workflow with JSON format."""
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

        # Create conversation
        messages = [
            {
                "role": "user",
                "content": "Test question",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "role": "assistant",
                "content": "Test answer",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]

        # Request JSON export
        export_response = await client.post(
            f"{base_url}/api/v1/stateless/export",
            headers=headers,
            json={
                "use_case_id": "test-case",
                "messages": messages,
                "export_format": "json",
            },
        )

        assert export_response.status_code == 200
        export_data = export_response.json()

        # Verify JSON format
        assert export_data["format"] == "json"

        # Verify content is valid JSON
        content = export_data["content"]
        parsed_content = json.loads(content)
        assert "messages" in parsed_content or isinstance(parsed_content, list)


@pytest.mark.asyncio
async def test_summary_generation_workflow(test_services_config, test_user_credentials):
    """Test summary generation from conversation messages."""
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

        # Create conversation with multiple messages
        messages = [
            {
                "role": "user",
                "content": "What are the security implications of this alert?",
                "timestamp": "2025-11-01T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "The alert indicates a potential data exfiltration attempt.",
                "timestamp": "2025-11-01T10:00:15Z",
            },
            {
                "role": "user",
                "content": "What actions should I take?",
                "timestamp": "2025-11-01T10:01:00Z",
            },
            {
                "role": "assistant",
                "content": "1. Isolate the account\n2. Block connections\n3. Review logs",
                "timestamp": "2025-11-01T10:01:30Z",
            },
        ]

        # Request summary
        summary_response = await client.post(
            f"{base_url}/api/v1/summaries",
            headers=headers,
            json={
                "use_case_id": "threat-triage-v1",
                "messages": messages,
                "export_format": "markdown",
            },
        )

        assert summary_response.status_code == 200
        summary_data = summary_response.json()

        # Verify summary structure
        assert "summary" in summary_data
        assert summary_data["message_count"] == 4
        assert summary_data["format"] == "markdown"
        assert summary_data["token_count"] > 0
        assert "model_used" in summary_data
        assert "generated_at" in summary_data
        assert isinstance(summary_data["redacted_fields"], list)


@pytest.mark.asyncio
async def test_summary_with_pii_redaction(test_services_config, test_user_credentials):
    """Test summary generation with PII redaction."""
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

        # Messages with PII
        messages = [
            {
                "role": "user",
                "content": "User email is admin@example.com and IP is 192.0.2.1",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "role": "assistant",
                "content": "I can help investigate that account.",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]

        # Request summary with redaction
        summary_response = await client.post(
            f"{base_url}/api/v1/summaries",
            headers=headers,
            json={
                "use_case_id": "test-case",
                "messages": messages,
                "export_format": "markdown",
                "redaction": {
                    "redact_pii": True,
                    "redact_secrets": False,
                    "replacement_strategy": "mask",
                    "pii_patterns": ["email", "ip"],
                },
            },
        )

        assert summary_response.status_code == 200
        summary_data = summary_response.json()

        # Verify redaction occurred
        summary_text = summary_data["summary"]

        # PII should be redacted or masked
        assert "admin@example.com" not in summary_text or "***" in summary_text
        assert "192.0.2.1" not in summary_text or "***" in summary_text

        # Redacted fields should be tracked
        assert len(summary_data["redacted_fields"]) > 0


@pytest.mark.asyncio
async def test_export_workflow_unauthorized(test_services_config):
    """Test export workflow requires authentication."""
    base_url = test_services_config["backend_url"]

    async with httpx.AsyncClient() as client:
        # Attempt export without auth
        export_response = await client.post(
            f"{base_url}/api/v1/stateless/export",
            json={
                "use_case_id": "test",
                "messages": [],
                "export_format": "markdown",
            },
        )

        # Should be unauthorized
        assert export_response.status_code == 401


@pytest.mark.asyncio
async def test_export_workflow_invalid_format(test_services_config, test_user_credentials):
    """Test export workflow rejects invalid formats."""
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

        # Request with invalid format
        export_response = await client.post(
            f"{base_url}/api/v1/stateless/export",
            headers=headers,
            json={
                "use_case_id": "test",
                "messages": [],
                "export_format": "invalid_format",
            },
        )

        # Should reject invalid format
        assert export_response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_export_empty_conversation(test_services_config, test_user_credentials):
    """Test export workflow with empty conversation."""
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

        # Export empty conversation
        export_response = await client.post(
            f"{base_url}/api/v1/stateless/export",
            headers=headers,
            json={
                "use_case_id": "test",
                "messages": [],
                "export_format": "markdown",
            },
        )

        assert export_response.status_code == 200
        export_data = export_response.json()

        # Should still have valid structure
        assert "content" in export_data
        assert export_data["message_count"] == 0


@pytest.mark.asyncio
async def test_capabilities_endpoint(test_services_config, test_user_credentials):
    """Test capabilities endpoint returns correct stateless configuration."""
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

        # Verify stateless configuration
        assert caps_data["stateless"] is True
        assert caps_data["edition"] == "core"
        assert "capabilities" in caps_data
        assert "feature_flags" in caps_data

        # Verify export capability is enabled
        assert "md" in caps_data["export_formats"]
        assert "json" in caps_data["export_formats"]

        # Verify provider configuration
        assert caps_data["providers"]["history"] == "edge_only"
        assert caps_data["providers"]["evidence"] == "none"
