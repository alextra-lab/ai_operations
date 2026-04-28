"""
Unit tests for AssemblePrompt pipeline step.

Tests the most complex step in the pipeline: prompt assembly with
multi-role prompts, history merging, and LLMRequest creation.
"""

import pytest

from src.orchestrator.app.orchestrator.context import RequestContext, RetrievalSource
from src.orchestrator.app.orchestrator.prompt_assembler import PromptAssembler
from src.orchestrator.app.orchestrator.steps.assemble_prompt import AssemblePrompt
from src.orchestrator.app.schemas.intent import IntentResponse, RequestType
from src.orchestrator.app.schemas.llm import LLMRequest
from src.orchestrator.app.schemas.prompt import PromptTemplate
from src.orchestrator.app.schemas.use_case_config import (
    GenerationParamsConfig,
    SamplingPreset,
    UseCaseConfig,
)


class MockPromptAssembler(PromptAssembler):
    """Mock assembler that returns template variables concatenated."""

    def __init__(self):
        # Don't call super().__init__() to avoid DB dependency
        pass

    def assemble_prompt(self, template: PromptTemplate, variables: dict) -> str:
        """Return a simple concatenation for testing."""
        return f"SYSTEM:{variables.get('system_prompt', '')}|QUERY:{variables.get('query', '')}"


@pytest.mark.asyncio
async def test_assemble_prompt_basic():
    """Test basic prompt assembly without prompts or history."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    ctx = RequestContext(
        req_id="test-1",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Find CVE details",
        query_sanitized="Find CVE details",
        intent=IntentResponse(
            query="Find CVE details",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    result = await step.run(ctx)

    # Verify LLMRequest was created
    assert result.llm_request is not None
    assert isinstance(result.llm_request, LLMRequest)
    assert result.llm_request.prompt != ""  # Should have assembled text
    assert result.llm_request.messages is None  # No multi-role prompts
    assert result.llm_request.temperature == 0.2  # Default
    assert result.llm_request.max_tokens == 1024  # Default


@pytest.mark.asyncio
async def test_assemble_prompt_with_multi_role_prompts():
    """Test prompt assembly with system, developer, and fewshots."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    ctx = RequestContext(
        req_id="test-2",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Analyze logs",
        query_sanitized="Analyze logs",
        intent=IntentResponse(
            query="Analyze logs",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts={
            "system_prompt": "You are a SOC analyst",
            "developer_prompt": "Extract IOCs in JSON",
            "fewshots": [
                {"user": "Find malware", "assistant": "Detected: trojan.exe"},
                {"user": "Check logs", "assistant": "Found: suspicious activity"},
            ],
        },
        history_messages=[],
        sources=[],
    )

    result = await step.run(ctx)

    # Verify messages array was built
    assert result.llm_request is not None
    assert result.llm_request.messages is not None
    assert result.llm_request.prompt == ""  # Multi-role uses messages, not prompt

    messages = result.llm_request.messages

    # Should have: system + 2 fewshots (user+assistant each) + current user query
    # = 1 system + 2 user + 2 assistant + 1 user = 6 messages
    assert len(messages) >= 5  # At least system + fewshots + query

    # Check system message combines system + developer
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    assert system_msg is not None
    assert "SOC analyst" in system_msg["content"]
    assert "Developer Instructions" in system_msg["content"]
    assert "Extract IOCs" in system_msg["content"]

    # Check fewshots are present
    user_messages = [m for m in messages if m["role"] == "user"]
    assert len(user_messages) >= 3  # 2 fewshots + 1 current

    # Check current query is last
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Analyze logs"


@pytest.mark.asyncio
async def test_assemble_prompt_with_history():
    """Test prompt assembly with conversation history."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    ctx = RequestContext(
        req_id="test-3",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Follow up question",
        query_sanitized="Follow up question",
        intent=IntentResponse(
            query="Follow up question",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts={"system_prompt": "You are helpful"},
        history_messages=history,
        sources=[],
    )

    result = await step.run(ctx)

    assert result.llm_request is not None
    assert result.llm_request.messages is not None

    messages = result.llm_request.messages

    # Should start with history
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Previous question"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Previous answer"


@pytest.mark.asyncio
async def test_assemble_prompt_with_sources():
    """Test prompt assembly with retrieved context sources."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    sources = [
        RetrievalSource(
            document_id="doc1",
            title="Security Guide",
            chunk_id="chunk1",
            score=0.95,
            metadata={"content": "IAL stands for Incident Alert Level"},
        ),
        RetrievalSource(
            document_id="doc2",
            title="Procedures",
            score=0.85,
            metadata={"content": "Follow escalation matrix"},
        ),
    ]

    ctx = RequestContext(
        req_id="test-4",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="What is IAL?",
        query_sanitized="What is IAL?",
        intent=IntentResponse(
            query="What is IAL?",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=sources,
    )

    result = await step.run(ctx)

    # Context should be included in the assembled prompt
    # The assembler receives variables["context"] with source titles and snippets
    assert result.llm_request is not None


@pytest.mark.asyncio
async def test_assemble_prompt_with_use_case_params():
    """Test prompt assembly with use case generation params."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    # Create use case config with generation params
    # Use CUSTOM preset to allow parameter overrides (ADR-023)
    gen_params = GenerationParamsConfig(
        sampling_preset=SamplingPreset.CUSTOM,
        temperature=0.85,
        max_tokens=4096,
    )

    use_case = UseCaseConfig(generation_params=gen_params)

    ctx = RequestContext(
        req_id="test-5",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Be creative",
        query_sanitized="Be creative",
        intent=IntentResponse(
            query="Be creative",
            detected_type=RequestType.QUERY,
            confidence=0.9,
            suggested_actions=[],
        ),
        use_case=use_case,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    result = await step.run(ctx)

    assert result.llm_request is not None
    assert result.llm_request.temperature == 0.85
    assert result.llm_request.max_tokens == 4096

    # Extra params should be in metrics
    assert result.llm_metrics["temperature"] == 0.85
    assert result.llm_metrics["max_tokens"] == 4096
    assert "top_p" in result.llm_metrics
    assert "frequency_penalty" in result.llm_metrics
    assert "presence_penalty" in result.llm_metrics


@pytest.mark.asyncio
async def test_assemble_prompt_error_fallback():
    """Test that errors are caught and fallback is provided."""

    # Create an assembler that throws an error
    class BrokenAssembler(PromptAssembler):
        def __init__(self):
            pass

        def assemble_prompt(self, template, variables):
            raise ValueError("Assembler broke!")

    step = AssemblePrompt(BrokenAssembler())

    ctx = RequestContext(
        req_id="test-6",
        user_id="user1",
        user_uuid=None,
        request_type=RequestType.QUERY,
        query_original="Test query",
        query_sanitized="Test query",
        intent=None,
        use_case=None,
        prompts=None,
        history_messages=[],
        sources=[],
    )

    result = await step.run(ctx)

    # Should have fallback request
    assert result.llm_request is not None
    assert result.llm_request.prompt == "Test query"
    assert result.llm_request.messages is None
    assert "assemble_prompt_error" in result.llm_metrics.get("fallbacks", [])


@pytest.mark.asyncio
async def test_assemble_prompt_model_preference_mapping():
    """Test RequestType → ModelType mapping."""
    assembler = MockPromptAssembler()
    step = AssemblePrompt(assembler)

    for request_type in [
        RequestType.QUERY,
        RequestType.SUMMARIZATION,
        RequestType.ENRICHMENT,
    ]:
        ctx = RequestContext(
            req_id=f"test-{request_type.value}",
            user_id="user1",
            user_uuid=None,
            request_type=request_type,
            query_original="Test",
            query_sanitized="Test",
            intent=IntentResponse(
                query="Test",
                detected_type=request_type,
                confidence=0.9,
                suggested_actions=[],
            ),
            use_case=None,
            prompts=None,
            history_messages=[],
            sources=[],
        )

        result = await step.run(ctx)

        assert result.llm_request is not None
        # Model preference should be set from intent
        assert result.llm_request.model_preference is not None
