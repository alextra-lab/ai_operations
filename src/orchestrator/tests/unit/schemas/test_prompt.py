import pytest
from app.schemas.intent import IntentResponse, RequestType
from app.schemas.prompt import PromptRequest, PromptResponse, PromptTemplate

# PromptTemplate tests


def test_prompt_template_valid():
    t = PromptTemplate(template_id="tid", template="Hello {query}", variables=["query"])
    assert t.template_id == "tid"
    assert t.template == "Hello {query}"
    assert t.variables == ["query"]


def test_prompt_template_empty_variables():
    with pytest.raises(ValueError):
        PromptTemplate(template_id="tid", template="Hello {query}", variables=[])


def test_prompt_template_missing_placeholder():
    with pytest.raises(ValueError):
        PromptTemplate(template_id="tid", template="Hello {foo}", variables=["query"])


def test_prompt_template_extra_placeholder():
    # Extra placeholder in template is allowed
    t = PromptTemplate(template_id="tid", template="Hello {query} {extra}", variables=["query"])
    assert "{extra}" in t.template


# PromptRequest tests


def test_prompt_request_valid():
    intent = IntentResponse(
        detected_type=RequestType.QUERY,
        explicit_type=RequestType.QUERY,
        inferred_type=None,
        confidence=1.0,
        query="Q",
        metadata={},
    )
    req = PromptRequest(intent=intent, context={"foo": "bar"})
    assert req.intent == intent
    assert req.context["foo"] == "bar"


# PromptResponse tests


def test_prompt_response_valid():
    resp = PromptResponse(prompt="Hi", template_id="tid", model="mistral-small", metadata={"x": 1})
    assert resp.prompt == "Hi"
    assert resp.template_id == "tid"
    assert resp.model == "mistral-small"
    assert resp.metadata["x"] == 1
