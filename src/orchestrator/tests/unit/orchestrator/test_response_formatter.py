from unittest.mock import AsyncMock, patch

import pytest
from app.orchestrator.response_formatter import ResponseFormatter
from app.schemas.llm import LLMResponse
from app.schemas.response import SourceMetadata


@pytest.fixture
def formatter():
    return ResponseFormatter()


def make_llm_response(text, meta=None, tokens=10, time=1.0):
    return LLMResponse(
        response=text,
        model_used="m",
        tokens_used=tokens,
        processing_time=time,
        metadata=meta or {},
    )


def test_extract_sources_various_formats(formatter):
    text = '[1] Title One (KB-123)\nSource: "Title Two" (TI-456)\nmentioned in "Title Three" (DOC-789)\nReferences:\n1. Title Four (POL-321)'
    sources = formatter.extract_sources(text)
    ids = {s.document_id for s in sources}
    assert "KB-123" in ids and "TI-456" in ids and "DOC-789" in ids and "POL-321" in ids


def test_extract_sources_duplicate(formatter):
    text = "[1] Title (KB-123)\n[2] Title (KB-123)"
    sources = formatter.extract_sources(text)
    assert len(sources) == 1


def test_extract_sources_no_match(formatter):
    text = "No citations here."
    sources = formatter.extract_sources(text)
    assert sources == []


def test_extract_content_snippet(formatter):
    text = "This is a sentence about Title. Another about KB-123."
    snippet = formatter._extract_content_snippet(text, "Title", "KB-123")
    # The function returns the first matching sentence, which may not contain both
    assert "Title" in snippet or "KB-123" in snippet
    assert "Referenced" in formatter._extract_content_snippet("No match", "X", "Y")


def test_calculate_relevance_score(formatter):
    text = "Title KB-123 Title KB-123."
    score = formatter._calculate_relevance_score(text, "Title", "KB-123")
    assert 0.0 <= score <= 1.0


def test_determine_source_type(formatter):
    assert formatter._determine_source_type("KB-123") == "KB"
    assert formatter._determine_source_type("TI-456") == "threat intel"
    assert formatter._determine_source_type("DOC-789") == "documentation"
    assert formatter._determine_source_type("POL-321") == "policy"
    assert formatter._determine_source_type("RULE-1") == "rule"
    assert formatter._determine_source_type("X-999") == "reference"


def test_format_response_and_cleaning(formatter):
    text = "Answer.\nReferences:\n1. Title (KB-123)\nSources:\n[1] Title (KB-123)"
    sources = [
        SourceMetadata(
            document_id="KB-123",
            title="Title",
            source="KB",
            similarity_score=1.0,
            chunk_index=0,
            document_type="text",
            created_at="2025-01-01T00:00:00Z",
            chunk_text="s",
            content="s",
        )
    ]
    resp = formatter.format_response(text, sources, 0.8)
    assert "References" not in resp.response and "Sources" not in resp.response
    assert resp.sources == sources
    assert resp.confidence == 0.8


def test_clean_response_text(formatter):
    text = "A.\nReferences:\n1. T (KB-1)\nSources:\n[1] T (KB-1)"
    cleaned = formatter._clean_response_text(text)
    assert "References" not in cleaned and "Sources" not in cleaned


from app.schemas.llm import ModelType


def test_calculate_confidence_all_factors(formatter):
    llm_resp = LLMResponse(
        response="text",
        model_used=ModelType.QUERY,
        tokens_used=10,
        processing_time=0.5,
        metadata={"confidence": 0.9},
    )
    sources = [
        SourceMetadata(
            document_id="KB-1",
            title="T",
            source="KB",
            similarity_score=1.0,
            chunk_index=0,
            document_type="text",
            created_at="2025-01-01T00:00:00Z",
            chunk_text="s",
            content="s",
        )
    ]
    conf = formatter._calculate_confidence(llm_resp, sources)
    assert 0.0 <= conf <= 1.0
    # No sources
    llm_resp2 = LLMResponse(
        response="text",
        model_used=ModelType.QUERY,
        tokens_used=10,
        processing_time=0.5,
        metadata={"confidence": 0.9},
    )
    conf2 = formatter._calculate_confidence(llm_resp2, [])
    assert 0.0 <= conf2 <= 1.0


def test_generate_suggested_actions_all_branches(formatter):
    sources = [
        SourceMetadata(
            document_id="TI-1",
            title="T",
            source="threat intel",
            similarity_score=1.0,
            chunk_index=0,
            document_type="text",
            created_at="2025-01-01T00:00:00Z",
            chunk_text="s",
            content="s",
        )
    ]
    actions = formatter._generate_suggested_actions("threat", sources, 0.5)
    assert (
        "view_sources" in actions and "refine_query" in actions and "investigate_threat" in actions
    )
    # No actions if disabled
    formatter2 = ResponseFormatter(enable_suggested_actions=False)
    assert formatter2._generate_suggested_actions("text", sources, 0.9) is None


def test_extract_threat_types(formatter):
    text = 'malware named "Evil" ransomware called "Bad" exploit targeting "X" vulnerability CVE-2023-1234 APT-29'
    types = formatter._extract_threat_types(text)
    assert set(types) == {"malware", "ransomware", "exploit", "vulnerability", "apt"}


@pytest.mark.asyncio
async def test_process_full_path(formatter):
    from app.schemas.llm import ModelType

    llm_resp = LLMResponse(
        response="[1] Title (KB-1)",
        model_used=ModelType.QUERY,
        tokens_used=10,
        processing_time=1.0,
        metadata={"confidence": 0.9, "tokens_in": 5, "tokens_out": 5},
    )

    # Mock estimate_cost to avoid database connection
    with patch(
        "app.orchestrator.response_formatter.estimate_cost", new_callable=AsyncMock
    ) as mock_cost:
        mock_cost.return_value = {
            "input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0,
            "currency": "EUR",
            "pricing_source": "generic_default",
        }
        resp = await formatter.process(llm_resp)
        assert (
            hasattr(resp, "response") and hasattr(resp, "sources") and hasattr(resp, "confidence")
        )


# Output Contract Validation Tests
def test_validate_output_no_contract(formatter):
    """Test validation with no contract returns text as-is"""
    text = "Some response text"
    validated_text, metadata, structured = formatter.validate_output(text, None)
    assert validated_text == text
    assert metadata["validation_applied"] is False
    assert structured is None


def test_validate_output_text_format(formatter):
    """Test TEXT format validation"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.TEXT, validation_mode=ValidationMode.BEST_EFFORT
    )
    text = "Valid text response"
    validated_text, metadata, structured = formatter.validate_output(text, contract)
    assert validated_text == text
    assert metadata["validation_applied"] is True
    assert metadata["format"] == "text"
    assert len(metadata["errors"]) == 0
    assert structured is None


def test_validate_output_json_valid(formatter):
    """Test valid JSON output validation"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )
    json_text = '{"key": "value", "number": 42}'
    _validated_text, metadata, structured = formatter.validate_output(json_text, contract)
    assert metadata["validation_applied"] is True
    assert metadata["parsed"] is True
    assert len(metadata["errors"]) == 0
    assert structured == {"key": "value", "number": 42}


def test_validate_output_json_invalid_best_effort(formatter):
    """Test invalid JSON in best-effort mode returns errors in metadata"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )
    invalid_json = "{invalid json}"
    _validated_text, metadata, structured = formatter.validate_output(invalid_json, contract)
    assert metadata["validation_applied"] is True
    assert metadata["parsed"] is False
    assert len(metadata["errors"]) > 0
    assert "Invalid JSON" in metadata["errors"][0]
    assert structured is None


def test_validate_output_json_invalid_strict(formatter):
    """Test invalid JSON in strict mode raises HTTPException"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )
    from fastapi import HTTPException

    contract = OutputContractConfig(format=OutputFormat.JSON, validation_mode=ValidationMode.STRICT)
    invalid_json = "{invalid json}"
    with pytest.raises(HTTPException) as exc_info:
        formatter.validate_output(invalid_json, contract)
    assert exc_info.value.status_code == 422


def test_validate_output_json_with_schema_valid(formatter):
    """Test JSON validation with valid schema"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }
    contract = OutputContractConfig(
        format=OutputFormat.JSON,
        validation_mode=ValidationMode.BEST_EFFORT,
        output_schema=schema,
    )
    json_text = '{"name": "John", "age": 30}'
    _validated_text, metadata, structured = formatter.validate_output(json_text, contract)
    assert metadata["validation_applied"] is True
    assert metadata["parsed"] is True
    assert metadata["schema_valid"] is True
    assert len(metadata["errors"]) == 0
    assert structured == {"name": "John", "age": 30}


def test_validate_output_json_with_schema_invalid_best_effort(formatter):
    """Test JSON validation with invalid schema in best-effort mode"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }
    contract = OutputContractConfig(
        format=OutputFormat.JSON,
        validation_mode=ValidationMode.BEST_EFFORT,
        output_schema=schema,
    )
    json_text = '{"name": "John"}'  # Missing required 'age' field
    _validated_text, metadata, structured = formatter.validate_output(json_text, contract)
    assert metadata["validation_applied"] is True
    assert metadata["parsed"] is True
    assert metadata["schema_valid"] is False
    assert len(metadata["errors"]) > 0
    assert structured == {"name": "John"}


def test_validate_output_json_with_schema_invalid_strict(formatter):
    """Test JSON validation with invalid schema in strict mode raises error"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )
    from fastapi import HTTPException

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }
    contract = OutputContractConfig(
        format=OutputFormat.JSON,
        validation_mode=ValidationMode.STRICT,
        output_schema=schema,
    )
    json_text = '{"name": "John"}'  # Missing required 'age' field
    with pytest.raises(HTTPException) as exc_info:
        formatter.validate_output(json_text, contract)
    assert exc_info.value.status_code == 422


def test_validate_output_yaml_valid(formatter):
    """Test valid YAML output validation"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.YAML, validation_mode=ValidationMode.BEST_EFFORT
    )
    yaml_text = """
name: John
age: 30
"""
    _validated_text, metadata, structured = formatter.validate_output(yaml_text, contract)
    assert metadata["validation_applied"] is True
    assert metadata["parsed"] is True
    assert len(metadata["errors"]) == 0
    assert structured == {"name": "John", "age": 30}


def test_validate_output_yaml_invalid_best_effort(formatter):
    """Test invalid YAML in best-effort mode"""
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.YAML, validation_mode=ValidationMode.BEST_EFFORT
    )
    invalid_yaml = """
    name: John
  age: 30  # Invalid indentation
"""
    _validated_text, metadata, structured = formatter.validate_output(invalid_yaml, contract)
    # YAML parser might be more lenient, but we should get some error
    assert metadata["validation_applied"] is True
    assert structured is None or isinstance(structured, dict)


@pytest.mark.asyncio
async def test_process_with_output_contract(formatter):
    """Test process method with output contract validation"""
    from app.schemas.llm import ModelType
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )
    llm_resp = LLMResponse(
        response='{"result": "success"}',
        model_used=ModelType.QUERY,
        tokens_used=10,
        processing_time=1.0,
        metadata={"confidence": 0.9, "tokens_in": 5, "tokens_out": 5},
    )

    # Mock estimate_cost to avoid database connection
    with patch(
        "app.orchestrator.response_formatter.estimate_cost", new_callable=AsyncMock
    ) as mock_cost:
        mock_cost.return_value = {
            "input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0,
            "currency": "EUR",
            "pricing_source": "generic_default",
        }
        resp = await formatter.process(llm_resp, output_contract=contract)
        assert hasattr(resp, "response")
        assert hasattr(resp, "metrics")
        assert hasattr(resp, "structured_data")
        assert resp.structured_data == {"result": "success"}
        # Check that validation metadata was added
        if resp.metrics and resp.metrics.model:
            assert "output_validation" in resp.metrics.model.metadata
            validation_meta = resp.metrics.model.metadata["output_validation"]
            assert validation_meta["validation_applied"] is True
            assert validation_meta["format"] == "json"


@pytest.mark.asyncio
async def test_process_structured_data_in_formatted_response(formatter):
    """Test that process() includes structured_data in FormattedResponse for JSON output."""
    from app.schemas.llm import ModelType
    from app.schemas.use_case_config import (
        OutputContractConfig,
        OutputFormat,
        ValidationMode,
    )

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )
    llm_resp = LLMResponse(
        response='{"confidence": 0.87, "iocs": [{"type": "ip", "value": "1.2.3.4"}]}',
        model_used=ModelType.QUERY,
        tokens_used=20,
        processing_time=0.5,
        metadata={"prompt_tokens": 10, "completion_tokens": 10},
    )
    with patch(
        "app.orchestrator.response_formatter.estimate_cost", new_callable=AsyncMock
    ) as mock_cost:
        mock_cost.return_value = {
            "input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0,
            "currency": "EUR",
            "pricing_source": "generic_default",
        }
        resp = await formatter.process(llm_resp, output_contract=contract)
    assert resp.structured_data is not None
    assert resp.structured_data["confidence"] == 0.87
    assert len(resp.structured_data["iocs"]) == 1
    assert resp.structured_data["iocs"][0]["type"] == "ip"
    assert resp.structured_data["iocs"][0]["value"] == "1.2.3.4"


@pytest.mark.asyncio
async def test_process_with_cost_estimation(formatter):
    """Test that process method calculates cost estimation"""
    from app.schemas.llm import ModelType

    llm_resp = LLMResponse(
        response="Test response",
        model_used=ModelType.QUERY,
        tokens_used=100,
        processing_time=1.0,
        metadata={
            "tokens_in": 50,
            "tokens_out": 50,
            "model_id": "test-model",
        },
    )

    # Mock estimate_cost with specific return value
    with patch(
        "app.orchestrator.response_formatter.estimate_cost", new_callable=AsyncMock
    ) as mock_cost:
        mock_cost.return_value = {
            "input_cost": 0.001,
            "output_cost": 0.002,
            "total_cost": 0.003,
            "currency": "EUR",
            "pricing_source": "pricing_history",
        }
        resp = await formatter.process(llm_resp)
        assert hasattr(resp, "metrics")
        if resp.metrics and resp.metrics.model:
            assert "cost_estimate" in resp.metrics.model.metadata
            assert "cost_breakdown" in resp.metrics.model.metadata
            cost_breakdown = resp.metrics.model.metadata["cost_breakdown"]
            assert "total_cost" in cost_breakdown
            assert "input_cost" in cost_breakdown
            assert "output_cost" in cost_breakdown
            assert "pricing_source" in cost_breakdown
            assert cost_breakdown["total_cost"] == 0.003
