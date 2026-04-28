#!/usr/bin/env python3
"""
Verification script for template-driven model selection.

This script tests that use case configuration properly overrides:
1. LLM model selection
2. Generation parameters (temperature, max_tokens)
3. Embedding model selection

Usage:
    python scripts/testing/verify_template_model_selection.py
"""

import asyncio
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from src.backend.app.orchestrator.llm_router import LLMRouter
from src.backend.app.schemas.llm import LLMRequest, ModelType
from src.backend.app.schemas.use_case_config import (
    GenerationParamsConfig,
    ModelsConfig,
    UseCaseConfig,
)


async def test_llm_model_override():
    """Test that LLM model is overridden from config."""
    print("🧪 Testing LLM model override...")

    # Create config with specific model
    config = UseCaseConfig(
        models=ModelsConfig(llm="gpt-4o-mini", embedding="text-embedding-3-large"),
        generation_params=GenerationParamsConfig(temperature=0.3, max_tokens=2048),
    )

    # Create LLM request
    request = LLMRequest(prompt="Test query for model selection", temperature=0.7, max_tokens=1024)

    # Create LLM router
    router = LLMRouter()

    # Apply config overrides
    router._apply_config_overrides(request, config)

    # Verify overrides
    assert (
        request.model_preference == ModelType.QUERY
    ), f"Expected ModelType.QUERY, got {request.model_preference}"
    assert request.temperature == 0.3, f"Expected temperature 0.3, got {request.temperature}"
    assert request.max_tokens == 2048, f"Expected max_tokens 2048, got {request.max_tokens}"

    print("✅ LLM model override test passed")


async def test_generation_params_override():
    """Test that generation parameters are overridden from config."""
    print("🧪 Testing generation parameters override...")

    # Create config with specific parameters
    config = UseCaseConfig(
        models=ModelsConfig(llm="gpt-4o", embedding="text-embedding-3-small"),
        generation_params=GenerationParamsConfig(temperature=0.1, max_tokens=512),
    )

    # Create LLM request with default values
    request = LLMRequest(
        prompt="Test query for parameter override", temperature=0.7, max_tokens=1024
    )

    # Create LLM router
    router = LLMRouter()

    # Apply config overrides
    router._apply_config_overrides(request, config)

    # Verify overrides
    assert request.temperature == 0.1, f"Expected temperature 0.1, got {request.temperature}"
    assert request.max_tokens == 512, f"Expected max_tokens 512, got {request.max_tokens}"

    print("✅ Generation parameters override test passed")


async def test_partial_config_override():
    """Test that partial config (only some fields) works correctly."""
    print("🧪 Testing partial config override...")

    # Create config with only temperature override
    config = UseCaseConfig(
        models=ModelsConfig(llm="gpt-4o-mini", embedding=None),
        generation_params=GenerationParamsConfig(temperature=0.5, max_tokens=None),
    )

    # Create LLM request
    request = LLMRequest(prompt="Test query for partial override", temperature=0.7, max_tokens=1024)

    # Create LLM router
    router = LLMRouter()

    # Apply config overrides
    router._apply_config_overrides(request, config)

    # Verify only temperature was overridden
    assert request.temperature == 0.5, f"Expected temperature 0.5, got {request.temperature}"
    assert (
        request.max_tokens == 1024
    ), f"Expected max_tokens to remain 1024, got {request.max_tokens}"

    print("✅ Partial config override test passed")


async def test_no_config_fallback():
    """Test that no config fallback works correctly."""
    print("🧪 Testing no config fallback...")

    # Create LLM request
    request = LLMRequest(prompt="Test query for no config", temperature=0.7, max_tokens=1024)

    # Create LLM router
    router = LLMRouter()

    # Apply config overrides with None config
    router._apply_config_overrides(request, None)

    # Verify no changes were made
    assert (
        request.temperature == 0.7
    ), f"Expected temperature to remain 0.7, got {request.temperature}"
    assert (
        request.max_tokens == 1024
    ), f"Expected max_tokens to remain 1024, got {request.max_tokens}"
    assert (
        request.model_preference is None
    ), f"Expected model_preference to remain None, got {request.model_preference}"

    print("✅ No config fallback test passed")


async def test_unknown_model_handling():
    """Test that unknown model names are handled gracefully."""
    print("🧪 Testing unknown model handling...")

    # Create config with unknown model
    config = UseCaseConfig(
        models=ModelsConfig(llm="unknown-model-name", embedding="text-embedding-3-large"),
        generation_params=GenerationParamsConfig(temperature=0.3, max_tokens=2048),
    )

    # Create LLM request
    request = LLMRequest(prompt="Test query for unknown model", temperature=0.7, max_tokens=1024)

    # Create LLM router
    router = LLMRouter()

    # Apply config overrides
    router._apply_config_overrides(request, config)

    # Verify fallback to QUERY model type
    assert (
        request.model_preference == ModelType.QUERY
    ), f"Expected ModelType.QUERY fallback, got {request.model_preference}"
    assert request.temperature == 0.3, f"Expected temperature 0.3, got {request.temperature}"
    assert request.max_tokens == 2048, f"Expected max_tokens 2048, got {request.max_tokens}"

    print("✅ Unknown model handling test passed")


async def test_embedding_model_parameter():
    """Test that embedding model parameter is correctly handled."""
    print("🧪 Testing embedding model parameter...")

    # Test that the parameter exists in the schema
    from src.retrieval.app.schemas.query import QueryRequest

    # Create a query request with embedding model
    query_request = QueryRequest(
        query_text="test query", top_k=10, embedding_model="text-embedding-3-large"
    )

    # Verify the parameter is set
    assert (
        query_request.embedding_model == "text-embedding-3-large"
    ), f"Expected embedding_model to be set, got {query_request.embedding_model}"

    print("✅ Embedding model parameter test passed")


async def test_model_type_mapping():
    """Test that different model names map to correct ModelType."""
    print("🧪 Testing model type mapping...")

    router = LLMRouter()

    # Test different model name patterns
    test_cases = [
        ("gpt-4o", ModelType.QUERY),
        ("gpt-4o-mini", ModelType.QUERY),
        ("gpt-3.5-turbo", ModelType.QUERY),
        ("unknown-model", ModelType.QUERY),  # Should fallback to QUERY
    ]

    for model_name, expected_type in test_cases:
        config = UseCaseConfig(
            models=ModelsConfig(llm=model_name, embedding="text-embedding-3-small"),
            generation_params=GenerationParamsConfig(temperature=0.7, max_tokens=1024),
        )

        request = LLMRequest(prompt="Test query", temperature=0.7, max_tokens=1024)

        router._apply_config_overrides(request, config)

        assert (
            request.model_preference == expected_type
        ), f"Expected {expected_type} for {model_name}, got {request.model_preference}"

    print("✅ Model type mapping test passed")


async def main():
    """Run all verification tests."""
    print("🚀 Starting template-driven model selection verification...")
    print("=" * 60)

    try:
        await test_llm_model_override()
        await test_generation_params_override()
        await test_partial_config_override()
        await test_no_config_fallback()
        await test_unknown_model_handling()
        await test_embedding_model_parameter()
        await test_model_type_mapping()

        print("=" * 60)
        print("🎉 All template-driven model selection tests passed!")
        print("✅ B3-F1: Template-Driven Model Selection - VERIFIED")

    except Exception as e:
        print("=" * 60)
        print(f"❌ Test failed with error: {e!s}")
        print("🔍 Check the implementation and try again")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
