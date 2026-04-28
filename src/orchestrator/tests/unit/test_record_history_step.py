"""
Unit tests for RecordHistory pipeline step (no-op stub).

Tests that RecordHistory behaves correctly as a no-op in Core Edition,
and is ready for Plus Edition v2+ implementation.
"""

import pytest
from app.orchestrator.context import RequestContext
from app.orchestrator.steps.record_history import RecordHistory
from app.schemas.intent import RequestType


@pytest.mark.asyncio
async def test_record_history_disabled_by_default():
    """Test RecordHistory is disabled by default (Core Edition)."""
    step = RecordHistory()

    assert step.enabled is False
    assert step.history is None
    assert step.tokens is None


@pytest.mark.asyncio
async def test_record_history_no_op_when_disabled():
    """Test RecordHistory returns context unchanged when disabled."""
    step = RecordHistory(history_service=None, token_tracker=None, enabled=False)

    ctx = RequestContext(
        req_id="test-1",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test query",
        query_sanitized="Test query",
        intent=None,
        use_case=None,
        prompts=None,
        thread_id=None,
        discussion_id=None,
        history_messages=[],
        sources=[],
        rag_enabled=False,
        llm_request=None,
        llm_response=None,
        formatted=None,
    )

    result = await step.run(ctx)

    # Should return exact same context (no modifications)
    assert result is ctx
    assert result.req_id == "test-1"
    assert result.user_id == "user1"
    assert result.query_original == "Test query"


@pytest.mark.asyncio
async def test_record_history_no_op_when_enabled():
    """Test RecordHistory still no-op when enabled=True (not implemented in Core)."""
    # Even with enabled=True, without history_service/token_tracker it's a no-op
    step = RecordHistory(history_service=None, token_tracker=None, enabled=True)

    ctx = RequestContext(
        req_id="test-2",
        user_id="user2",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Another query",
        query_sanitized="Another query",
        intent=None,
        use_case=None,
        prompts=None,
        thread_id=None,
        discussion_id=None,
        history_messages=[],
        sources=[],
        rag_enabled=False,
        llm_request=None,
        llm_response=None,
        formatted=None,
    )

    result = await step.run(ctx)

    # Should still return unchanged context (Plus Edition not implemented)
    assert result is ctx
    assert result.req_id == "test-2"
    assert result.user_id == "user2"


@pytest.mark.asyncio
async def test_record_history_accepts_services_for_plus_edition():
    """Test RecordHistory can accept services (ready for Plus Edition v2+)."""
    # Mock services (would be real in Plus Edition)
    mock_history = object()
    mock_tracker = object()

    step = RecordHistory(history_service=mock_history, token_tracker=mock_tracker, enabled=False)

    assert step.history is mock_history
    assert step.tokens is mock_tracker
    assert step.enabled is False


@pytest.mark.asyncio
async def test_record_history_preserves_all_context_fields():
    """Test RecordHistory preserves all context fields without modification."""
    step = RecordHistory(history_service=None, token_tracker=None, enabled=False)

    ctx = RequestContext(
        req_id="test-3",
        user_id="user3",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Complex query",
        query_sanitized="Complex query sanitized",
        intent=None,
        use_case=None,
        prompts={"system_prompt": "You are helpful"},
        thread_id=None,
        discussion_id="incident-123",
        history_messages=[
            {"role": "user", "content": "Previous"},
            {"role": "assistant", "content": "Response"},
        ],
        sources=[],
        rag_enabled=True,
        llm_request=None,
        llm_response=None,
        formatted=None,
    )

    result = await step.run(ctx)

    # Verify all fields preserved
    assert result.req_id == "test-3"
    assert result.user_id == "user3"
    assert result.query_sanitized == "Complex query sanitized"
    assert result.prompts == {"system_prompt": "You are helpful"}
    assert result.discussion_id == "incident-123"
    assert len(result.history_messages) == 2
    assert result.rag_enabled is True
