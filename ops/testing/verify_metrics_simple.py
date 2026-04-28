#!/usr/bin/env python3
"""
Simple verification script for B2-F2: Enhanced Metrics in Response

This script tests the metrics schemas and response structure without requiring authentication.
It validates that the enhanced metrics are properly implemented in the code.

Usage:
    python scripts/testing/verify_metrics_simple.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.app.schemas.response import (
    ConsolidatedMetrics,
    FormattedResponse,
    GuardMetrics,
    ModelMetrics,
    RetrievalMetrics,
)


def test_metrics_schemas():
    """Test that all metrics schemas are properly defined."""
    print("🧪 Testing Enhanced Metrics Schemas...")

    # Test RetrievalMetrics
    try:
        retrieval = RetrievalMetrics(
            top_k=10,
            hits=5,
            avg_similarity=0.85,
            min_similarity=0.72,
            max_similarity=0.95,
            source_count=3,
        )
        print("✅ RetrievalMetrics schema works")
    except Exception as e:
        print(f"❌ RetrievalMetrics schema error: {e}")
        return False

    # Test GuardMetrics
    try:
        guard = GuardMetrics(
            risk_score=0.15, modified=False, details={"prompt_injection": False, "toxicity": 0.1}
        )
        print("✅ GuardMetrics schema works")
    except Exception as e:
        print(f"❌ GuardMetrics schema error: {e}")
        return False

    # Test ModelMetrics
    try:
        model = ModelMetrics(
            model_id="gpt-4o-mini",
            tokens_in=150,
            tokens_out=300,
            total_tokens=450,
            processing_time=2.5,
            metadata={"temperature": 0.7},
        )
        print("✅ ModelMetrics schema works")
    except Exception as e:
        print(f"❌ ModelMetrics schema error: {e}")
        return False

    # Test ConsolidatedMetrics
    try:
        consolidated = ConsolidatedMetrics(
            retrieval=retrieval,
            guard=guard,
            model=model,
            confidence_score=0.87,
            calculation_method="weighted_consolidation",
        )
        print("✅ ConsolidatedMetrics schema works")
    except Exception as e:
        print(f"❌ ConsolidatedMetrics schema error: {e}")
        return False

    # Test FormattedResponse with metrics
    try:
        FormattedResponse(
            response="This is a test response with comprehensive metrics.",
            sources=[],
            confidence=0.87,
            metrics=consolidated,
            suggested_actions=None,
            request_id="test-request-123",
        )
        print("✅ FormattedResponse with metrics works")
    except Exception as e:
        print(f"❌ FormattedResponse with metrics error: {e}")
        return False

    return True


def test_confidence_calculation():
    """Test the confidence calculation logic."""
    print("\n🧪 Testing Confidence Calculation...")

    # Import the ResponseFormatter to test confidence calculation
    try:
        from src.backend.app.orchestrator.response_formatter import ResponseFormatter

        formatter = ResponseFormatter()

        # Test consolidated confidence calculation
        retrieval = RetrievalMetrics(
            top_k=10,
            hits=5,
            avg_similarity=0.85,
            min_similarity=0.72,
            max_similarity=0.95,
            source_count=3,
        )

        guard = GuardMetrics(risk_score=0.15, modified=False, details={})

        model = ModelMetrics(
            model_id="gpt-4o-mini",
            tokens_in=150,
            tokens_out=300,
            total_tokens=450,
            processing_time=2.5,
            metadata={},
        )

        # Test confidence calculation
        confidence = formatter._calculate_consolidated_confidence(retrieval, guard, model, [])

        if 0.0 <= confidence <= 1.0:
            print(f"✅ Confidence calculation works: {confidence:.3f}")
        else:
            print(f"❌ Invalid confidence score: {confidence}")
            return False

    except Exception as e:
        print(f"❌ Confidence calculation test error: {e}")
        return False

    return True


def test_metrics_consolidation():
    """Test the metrics consolidation logic."""
    print("\n🧪 Testing Metrics Consolidation...")

    try:
        from src.backend.app.orchestrator.response_formatter import ResponseFormatter
        from src.backend.app.schemas.llm import LLMResponse, ModelType

        formatter = ResponseFormatter()

        # Create mock LLM response
        llm_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,
            tokens_used=450,
            processing_time=2.5,
            metadata={"tokens_in": 150, "tokens_out": 300},
        )

        # Test metrics consolidation
        retrieval_metrics = {
            "top_k": 10,
            "hits": 5,
            "similarity_scores": [0.95, 0.85, 0.75, 0.72, 0.80],
            "source_count": 3,
        }

        guard_metrics = {
            "risk_score": 0.15,
            "modified": False,
            "details": {"prompt_injection": False},
        }

        consolidated = formatter._consolidate_metrics(
            llm_response, [], retrieval_metrics, guard_metrics
        )

        # Validate consolidated metrics
        if consolidated.retrieval and consolidated.guard and consolidated.model:
            print("✅ Metrics consolidation works")
            print(f"   - Retrieval: {consolidated.retrieval.avg_similarity:.3f}")
            print(f"   - Guard: {consolidated.guard.risk_score:.3f}")
            print(f"   - Model: {consolidated.model.model_id}")
            print(f"   - Confidence: {consolidated.confidence_score:.3f}")
        else:
            print("❌ Metrics consolidation failed - missing components")
            return False

    except Exception as e:
        print(f"❌ Metrics consolidation test error: {e}")
        return False

    return True


def main():
    """Main verification function."""
    print("🚀 Enhanced Metrics Simple Verification Script")
    print("=" * 60)

    success = True

    # Test schemas
    if not test_metrics_schemas():
        success = False

    # Test confidence calculation
    if not test_confidence_calculation():
        success = False

    # Test metrics consolidation
    if not test_metrics_consolidation():
        success = False

    if success:
        print("\n🎉 All Enhanced Metrics Tests Passed!")
        print("✅ B2-F2: Enhanced Metrics in Response - SCHEMA IMPLEMENTATION COMPLETE")
        print("\n📋 Implementation Summary:")
        print("   ✅ RetrievalMetrics schema with min/max similarity")
        print("   ✅ GuardMetrics schema with risk score and details")
        print("   ✅ ModelMetrics schema with token tracking")
        print("   ✅ ConsolidatedMetrics with weighted confidence")
        print("   ✅ FormattedResponse includes comprehensive metrics")
        print("   ✅ ResponseFormatter consolidates all metrics")
        print("   ✅ Confidence calculation using weighted formula")
        return 0
    print("\n❌ Enhanced Metrics Tests Failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
