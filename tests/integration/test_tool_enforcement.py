"""
Integration tests for tool enforcement.

Tests the integration of tool validation with the orchestrator
and use case configuration system.

P5-A20: Migrated to async database patterns (ADR-022).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import UseCase
from src.orchestrator.app.orchestrator.controller import Orchestrator
from src.orchestrator.app.schemas.intent import RequestType


@pytest.mark.asyncio
async def test_use_case_with_empty_tool_allowlist(db_session: AsyncSession, user_token: str):
    """
    Test that use case with empty tool allowlist allows all tools.

    This test verifies that the tool validation logs properly when
    no tools are restricted.
    """
    # Create a use case with empty tools_allowlist
    use_case = UseCase(
        use_case_id="test_no_tools",
        name="Test No Tools Restriction",
        description="Test use case with no tool restrictions",
        category="security",
        intent_type=RequestType.QUERY.value,
        is_active=True,
        lifecycle_state="published",
        config_json={
            "visibility": {"roles": ["admin", "user"]},
            "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
            "rag": {"enabled": True, "top_k": 10},
            "tools_allowlist": [],  # Empty = allow all
            "policy": {"streaming_default": False},
        },
    )
    db_session.add(use_case)
    await db_session.commit()

    # Create orchestrator
    orchestrator = Orchestrator(async_db=db_session)

    # Process a query - should work without issues
    result = await orchestrator.process(  # type: ignore[attr-defined]
        query="What is threat intelligence?",
        request_type=RequestType.QUERY,
        token=user_token,
        stream=False,
    )

    # Should succeed
    assert result is not None
    assert hasattr(result, "response_text")


@pytest.mark.asyncio
async def test_use_case_with_tool_allowlist(db_session: AsyncSession, user_token: str, caplog):
    """
    Test that use case with tool allowlist logs validation warnings.

    Since tool calling is not yet implemented, this should log
    a warning about future MCP integration.
    """
    # Create a use case with specific tools in allowlist
    use_case = UseCase(
        use_case_id="test_with_tools",
        name="Test With Tools",
        description="Test use case with tool restrictions",
        category="security",
        intent_type=RequestType.QUERY.value,
        is_active=True,
        lifecycle_state="published",
        config_json={
            "visibility": {"roles": ["admin", "user"]},
            "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
            "rag": {"enabled": True, "top_k": 10},
            "tools_allowlist": ["web_search", "threat_intel_lookup"],
            "policy": {"streaming_default": False},
        },
    )
    db_session.add(use_case)
    await db_session.commit()

    # Create orchestrator
    orchestrator = Orchestrator(async_db=db_session)

    # Process a query
    result = await orchestrator.process(  # type: ignore[attr-defined]
        query="What is threat intelligence?",
        request_type=RequestType.QUERY,
        token=user_token,
        stream=False,
    )

    # Should succeed
    assert result is not None

    # Should log warning about tool calling not implemented
    assert any("Tool calling is not yet implemented" in record.message for record in caplog.records)

    # Should log the configured tools
    assert any(
        "web_search" in record.message and "threat_intel_lookup" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_use_case_with_invalid_tool_name(db_session: AsyncSession, user_token: str):
    """
    Test that use case with invalid tool names raises validation error.

    Tool names must be non-empty strings.
    """
    # Create a use case with invalid tool name
    use_case = UseCase(
        use_case_id="test_invalid_tools",
        name="Test Invalid Tools",
        description="Test use case with invalid tool names",
        category="security",
        intent_type=RequestType.QUERY.value,
        is_active=True,
        lifecycle_state="published",
        config_json={
            "visibility": {"roles": ["admin", "user"]},
            "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
            "rag": {"enabled": True, "top_k": 10},
            "tools_allowlist": ["web_search", "", "  "],  # Invalid: empty and whitespace
            "policy": {"streaming_default": False},
        },
    )
    db_session.add(use_case)
    await db_session.commit()

    # Create orchestrator
    orchestrator = Orchestrator(async_db=db_session)

    # Process a query - should raise validation error
    with pytest.raises(ValueError, match="invalid tool name"):
        await orchestrator.process(  # type: ignore[attr-defined]
            query="What is threat intelligence?",
            request_type=RequestType.QUERY,
            token=user_token,
            stream=False,
        )


@pytest.mark.asyncio
async def test_tool_validator_integration_with_config_loader(db_session: AsyncSession):
    """
    Test that tool validator integrates correctly with config loader.

    This tests the full workflow: DB → Config Loader → Validator
    """
    # Create use cases with different tool configurations
    use_cases = [
        UseCase(
            use_case_id="no_tools",
            name="No Tools",
            description="No tool restrictions",
            category="security",
            intent_type=RequestType.QUERY.value,
            is_active=True,
            lifecycle_state="published",
            config_json={
                "visibility": {"roles": ["admin"]},
                "models": {"llm": "gpt-4o"},
                "rag": {"enabled": True, "top_k": 10},
                "tools_allowlist": [],
                "policy": {"streaming_default": False},
            },
        ),
        UseCase(
            use_case_id="with_tools",
            name="With Tools",
            description="Specific tools allowed",
            category="security",
            intent_type=RequestType.SUMMARIZATION.value,
            is_active=True,
            lifecycle_state="published",
            config_json={
                "visibility": {"roles": ["admin"]},
                "models": {"llm": "gpt-4o"},
                "rag": {"enabled": True, "top_k": 10},
                "tools_allowlist": ["web_search", "code_interpreter"],
                "policy": {"streaming_default": True},
            },
        ),
    ]

    for uc in use_cases:
        db_session.add(uc)
    await db_session.commit()

    # Create orchestrator
    orchestrator = Orchestrator(async_db=db_session)

    # Load configs
    config1 = await orchestrator.load_use_case_config(RequestType.QUERY)
    config2 = await orchestrator.load_use_case_config(RequestType.SUMMARIZATION)

    # Verify configs loaded correctly
    assert config1.tools_allowlist == []
    assert config2.tools_allowlist == ["web_search", "code_interpreter"]

    # Validate tools (should not raise errors for valid configs)
    orchestrator._validate_tool_allowlist(config1)
    orchestrator._validate_tool_allowlist(config2)


@pytest.mark.asyncio
async def test_tool_enforcement_logs_correctly(db_session: AsyncSession, user_token: str, caplog):
    """
    Test that tool enforcement logs messages at appropriate levels.

    - INFO for configured tools
    - WARNING for not-yet-implemented tools
    - DEBUG for empty allowlists
    """
    import logging

    caplog.set_level(logging.DEBUG)

    # Create use case with tools
    use_case = UseCase(
        use_case_id="logging_test",
        name="Logging Test",
        description="Test logging behavior",
        category="security",
        intent_type=RequestType.QUERY.value,
        is_active=True,
        lifecycle_state="published",
        config_json={
            "visibility": {"roles": ["admin", "user"]},
            "models": {"llm": "gpt-4o"},
            "rag": {"enabled": True, "top_k": 10},
            "tools_allowlist": ["web_search"],
            "policy": {"streaming_default": False},
        },
    )
    db_session.add(use_case)
    await db_session.commit()

    # Create orchestrator
    orchestrator = Orchestrator(async_db=db_session)

    # Process query
    await orchestrator.process(  # type: ignore[attr-defined]
        query="Test query", request_type=RequestType.QUERY, token=user_token, stream=False
    )

    # Check log levels
    info_logs = [r for r in caplog.records if r.levelname == "INFO"]
    warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]

    # Should have INFO log about tool allowlist
    assert any("Tool allowlist configured" in r.message for r in info_logs)

    # Should have WARNING about not implemented
    assert any("Tool calling is not yet implemented" in r.message for r in warning_logs)


@pytest.mark.asyncio
async def test_default_config_has_empty_tool_allowlist(db_session: AsyncSession):
    """
    Test that default config has empty tool allowlist (allow all).
    """
    orchestrator = Orchestrator(async_db=db_session)

    # Load default config (when no specific use case exists)
    config = orchestrator.config_loader.get_default_config()

    # Default should have empty allowlist
    assert config.tools_allowlist == []
