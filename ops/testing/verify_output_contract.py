#!/usr/bin/env python3
"""
Verification script for B3-F4: Output Contract Validation.

This script tests the output contract validation feature by:
1. Testing JSON format validation
2. Testing YAML format validation
3. Testing schema validation (valid and invalid)
4. Testing best-effort vs strict modes
5. Testing integration with ResponseFormatter

Usage:
    python scripts/testing/verify_output_contract.py
"""

import os
import sys

# Add src/backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/backend"))

from app.orchestrator.response_formatter import ResponseFormatter
from app.schemas.llm import LLMResponse, ModelType
from app.schemas.use_case_config import OutputContractConfig, OutputFormat, ValidationMode


def test_json_validation_valid():
    """Test 1: Valid JSON output validation"""
    print("\n=== Test 1: Valid JSON Output Validation ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )

    json_output = '{"result": "success", "data": {"count": 42}}'
    _validated_text, metadata = formatter.validate_output(json_output, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert metadata["parsed"], "JSON should be parsed successfully"
    assert len(metadata["errors"]) == 0, "Should have no errors"

    print("✅ Valid JSON validation passed")
    print(f"   Parsed: {metadata['parsed']}")
    print(f"   Errors: {len(metadata['errors'])}")
    return True


def test_json_validation_invalid_best_effort():
    """Test 2: Invalid JSON in best-effort mode"""
    print("\n=== Test 2: Invalid JSON in Best-Effort Mode ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )

    invalid_json = "{invalid json content}"
    _validated_text, metadata = formatter.validate_output(invalid_json, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert not metadata["parsed"], "Invalid JSON should fail to parse"
    assert len(metadata["errors"]) > 0, "Should have validation errors"
    assert "Invalid JSON" in metadata["errors"][0], "Error should mention Invalid JSON"

    print("✅ Invalid JSON best-effort mode passed")
    print(f"   Parsed: {metadata['parsed']}")
    print(f"   Errors: {metadata['errors']}")
    return True


def test_json_validation_invalid_strict():
    """Test 3: Invalid JSON in strict mode raises exception"""
    print("\n=== Test 3: Invalid JSON in Strict Mode ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(format=OutputFormat.JSON, validation_mode=ValidationMode.STRICT)

    invalid_json = "{invalid json content}"

    try:
        formatter.validate_output(invalid_json, contract)
        print("❌ Should have raised HTTPException")
        return False
    except Exception as e:
        assert hasattr(e, "status_code"), "Should be HTTPException"
        assert e.status_code == 422, "Should be 422 status code"
        print("✅ Invalid JSON strict mode raised HTTPException as expected")
        print(f"   Status Code: {e.status_code}")
        print(f"   Detail: {e.detail}")
        return True


def test_json_schema_validation_valid():
    """Test 4: JSON schema validation with valid data"""
    print("\n=== Test 4: JSON Schema Validation (Valid) ===")

    formatter = ResponseFormatter()
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "email": {"type": "string"},
        },
        "required": ["name", "age"],
    }

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT, output_schema=schema
    )

    valid_json = '{"name": "John Doe", "age": 30, "email": "john@example.com"}'
    _validated_text, metadata = formatter.validate_output(valid_json, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert metadata["parsed"], "JSON should be parsed"
    assert metadata["schema_valid"], "Schema should be valid"
    assert len(metadata["errors"]) == 0, "Should have no errors"

    print("✅ Valid JSON schema validation passed")
    print(f"   Schema Valid: {metadata['schema_valid']}")
    print(f"   Errors: {len(metadata['errors'])}")
    return True


def test_json_schema_validation_invalid_best_effort():
    """Test 5: JSON schema validation with invalid data in best-effort mode"""
    print("\n=== Test 5: JSON Schema Validation (Invalid, Best-Effort) ===")

    formatter = ResponseFormatter()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT, output_schema=schema
    )

    invalid_json = '{"name": "John Doe"}'  # Missing required 'age' field
    _validated_text, metadata = formatter.validate_output(invalid_json, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert metadata["parsed"], "JSON should be parsed"
    assert not metadata["schema_valid"], "Schema should be invalid"
    assert len(metadata["errors"]) > 0, "Should have validation errors"

    print("✅ Invalid JSON schema best-effort mode passed")
    print(f"   Schema Valid: {metadata['schema_valid']}")
    print(f"   Errors: {metadata['errors']}")
    return True


def test_json_schema_validation_invalid_strict():
    """Test 6: JSON schema validation with invalid data in strict mode"""
    print("\n=== Test 6: JSON Schema Validation (Invalid, Strict) ===")

    formatter = ResponseFormatter()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }

    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.STRICT, output_schema=schema
    )

    invalid_json = '{"name": "John Doe"}'  # Missing required 'age' field

    try:
        formatter.validate_output(invalid_json, contract)
        print("❌ Should have raised HTTPException")
        return False
    except Exception as e:
        assert hasattr(e, "status_code"), "Should be HTTPException"
        assert e.status_code == 422, "Should be 422 status code"
        print("✅ Invalid JSON schema strict mode raised HTTPException as expected")
        print(f"   Status Code: {e.status_code}")
        return True


def test_yaml_validation_valid():
    """Test 7: Valid YAML output validation"""
    print("\n=== Test 7: Valid YAML Output Validation ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(
        format=OutputFormat.YAML, validation_mode=ValidationMode.BEST_EFFORT
    )

    yaml_output = """
name: John Doe
age: 30
email: john@example.com
"""
    _validated_text, metadata = formatter.validate_output(yaml_output, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert metadata["parsed"], "YAML should be parsed successfully"
    assert len(metadata["errors"]) == 0, "Should have no errors"

    print("✅ Valid YAML validation passed")
    print(f"   Parsed: {metadata['parsed']}")
    print(f"   Errors: {len(metadata['errors'])}")
    return True


def test_text_format_validation():
    """Test 8: TEXT format validation"""
    print("\n=== Test 8: TEXT Format Validation ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(
        format=OutputFormat.TEXT, validation_mode=ValidationMode.BEST_EFFORT
    )

    text_output = "This is a plain text response."
    validated_text, metadata = formatter.validate_output(text_output, contract)

    assert metadata["validation_applied"], "Validation should be applied"
    assert validated_text == text_output, "Text should remain unchanged"
    assert len(metadata["errors"]) == 0, "Should have no errors"

    print("✅ TEXT format validation passed")
    print(f"   Format: {metadata['format']}")
    print(f"   Errors: {len(metadata['errors'])}")
    return True


def test_no_contract():
    """Test 9: Validation with no contract"""
    print("\n=== Test 9: No Contract Validation ===")

    formatter = ResponseFormatter()
    text = "Some response text"
    validated_text, metadata = formatter.validate_output(text, None)

    assert not metadata["validation_applied"], "Validation should not be applied"
    assert validated_text == text, "Text should remain unchanged"

    print("✅ No contract validation passed")
    print(f"   Validation Applied: {metadata['validation_applied']}")
    return True


def test_process_with_output_contract():
    """Test 10: Integration with ResponseFormatter.process()"""
    print("\n=== Test 10: Integration with ResponseFormatter.process() ===")

    formatter = ResponseFormatter()
    contract = OutputContractConfig(
        format=OutputFormat.JSON, validation_mode=ValidationMode.BEST_EFFORT
    )

    llm_response = LLMResponse(
        response='{"result": "success", "confidence": 0.95}',
        model_used=ModelType.QUERY,
        tokens_used=50,
        processing_time=1.2,
        metadata={"confidence": 0.9, "tokens_in": 20, "tokens_out": 30},
    )

    formatted_response = formatter.process(
        llm_response, request_id="test-request-123", output_contract=contract
    )

    assert formatted_response is not None, "Should return formatted response"
    assert formatted_response.metrics is not None, "Should have metrics"
    assert formatted_response.metrics.model is not None, "Should have model metrics"
    assert (
        "output_validation" in formatted_response.metrics.model.metadata
    ), "Should have output validation metadata"

    validation_meta = formatted_response.metrics.model.metadata["output_validation"]
    assert validation_meta["validation_applied"], "Validation should be applied"
    assert validation_meta["format"] == "json", "Format should be JSON"

    print("✅ Integration with ResponseFormatter.process() passed")
    print(f"   Validation Applied: {validation_meta['validation_applied']}")
    print(f"   Format: {validation_meta['format']}")
    print(f"   Parsed: {validation_meta.get('parsed', 'N/A')}")
    return True


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("B3-F4: Output Contract Validation - Verification Script")
    print("=" * 60)

    tests = [
        ("JSON Validation (Valid)", test_json_validation_valid),
        ("JSON Validation (Invalid, Best-Effort)", test_json_validation_invalid_best_effort),
        ("JSON Validation (Invalid, Strict)", test_json_validation_invalid_strict),
        ("JSON Schema Validation (Valid)", test_json_schema_validation_valid),
        (
            "JSON Schema Validation (Invalid, Best-Effort)",
            test_json_schema_validation_invalid_best_effort,
        ),
        ("JSON Schema Validation (Invalid, Strict)", test_json_schema_validation_invalid_strict),
        ("YAML Validation (Valid)", test_yaml_validation_valid),
        ("TEXT Format Validation", test_text_format_validation),
        ("No Contract Validation", test_no_contract),
        ("Integration Test", test_process_with_output_contract),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} failed with exception: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Verification Results: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ All tests passed successfully!")
        print("=" * 60)
        return 0
    print(f"❌ {failed} test(s) failed")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
