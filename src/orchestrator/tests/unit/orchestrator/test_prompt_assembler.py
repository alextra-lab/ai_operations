from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.orchestrator.prompt_assembler import PromptAssembler
from app.schemas.intent import IntentResponse, RequestType
from app.schemas.prompt import PromptRequest, PromptTemplate


@pytest.fixture
def assembler():
    db = MagicMock()
    return PromptAssembler(db)


def make_template(vars=None, template_id="tid", template="Hello {query} {context}"):
    return PromptTemplate(
        template_id=template_id,
        template=template,
        variables=vars or ["query", "context"],
    )


@pytest.mark.asyncio
async def test_select_template_valid(assembler):
    assembler.template_loader.get_template = AsyncMock(return_value=make_template())
    t = await assembler.select_template(RequestType.QUERY)
    assert isinstance(t, PromptTemplate)


@pytest.mark.asyncio
async def test_select_template_invalid_intent(assembler):
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        t = await assembler.select_template("not_a_real_intent")
        assert t is None
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_select_template_template_not_found(assembler):
    assembler.template_loader.get_template = AsyncMock(return_value=None)
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        t = await assembler.select_template(RequestType.QUERY)
        assert t is None
        assert mock_logger.error.called


def test_assemble_prompt_all_vars(assembler):
    t = make_template()
    variables = {"query": "Q", "context": "C"}
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        prompt = assembler.assemble_prompt(t, variables)
        assert "Q" in prompt and "C" in prompt
        assert mock_logger.info.called


def test_assemble_prompt_missing_vars(assembler):
    t = make_template()
    variables = {"query": "Q"}
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        prompt = assembler.assemble_prompt(t, variables)
        assert "Q" in prompt
        assert mock_logger.error.called


def test_assemble_prompt_keyerror(assembler):
    t = make_template(["query", "context", "missing"], template="Hi {query} {context} {missing}")
    variables = {"query": "Q", "context": "C"}
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        prompt = assembler.assemble_prompt(t, variables)
        # The code fills missing variables with empty string, so no error is raised
        assert prompt == "Hi Q C "
        assert mock_logger.error.called


import pytest
from pydantic import ValidationError


def test_assemble_prompt_valueerror(assembler):
    with pytest.raises(ValidationError):
        assembler.assemble_prompt(
            PromptTemplate(template_id="tid", template="Hi {query!bad}", variables=["query"]),
            {"query": "Q"},
        )


@pytest.mark.asyncio
async def test_get_prompt_no_template(assembler):
    intent = IntentResponse(
        detected_type=RequestType.QUERY,
        explicit_type=RequestType.QUERY,
        inferred_type=None,
        confidence=1.0,
        query="Q",
        metadata={},
    )
    assembler.select_template = AsyncMock(return_value=None)
    with patch("app.orchestrator.prompt_assembler.logger") as mock_logger:
        req = PromptRequest(intent=intent, context=None)
        resp = await assembler.get_prompt(req)
        assert "ERROR" in resp.prompt
        assert resp.template_id == "error"
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_get_prompt_normal(assembler):
    intent = IntentResponse(
        detected_type=RequestType.QUERY,
        explicit_type=RequestType.QUERY,
        inferred_type=None,
        confidence=1.0,
        query="Q",
        metadata={},
    )
    t = make_template()
    assembler.select_template = AsyncMock(return_value=t)
    assembler.assemble_prompt = MagicMock(return_value="Prompted!")
    req = PromptRequest(intent=intent, context={"foo": "bar"})
    resp = await assembler.get_prompt(req)
    assert resp.prompt == "Prompted!"
    assert resp.template_id == t.template_id
    assert resp.model == "mistral-small"
    assert resp.metadata["intent_type"] == RequestType.QUERY.value
