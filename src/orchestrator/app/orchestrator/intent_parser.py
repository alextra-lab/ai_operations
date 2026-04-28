"""
Intent Parser for AI Operations Platform.

This module implements the Intent Parser component of the orchestrator,
which classifies incoming requests into specific types for appropriate routing
and processing.

For MVP: Intent determination is deterministic based on explicit parameters provided by
the UI or Automation Source (SOAR playbook).

Future: Will add NLP-based intent detection to analyze query text for intent classification.
"""

import os
import time

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import IntentRequest, IntentResponse, RequestType

logger = configure_logging(service_name="intent_parser", log_level="INFO", log_format="json")


class IntentParser:
    """
    Intent Parser Component for the Orchestrator.

    This component analyzes incoming requests to determine their intent type,
    enabling appropriate routing and processing within the system.

    For MVP: Uses a simple deterministic approach based on the explicit request_type.
    Future: Will incorporate NLP-based intent detection for automatic classification.

    Future Enhancements:
    - NLP-based intent detection using text analysis
    - Comparison of explicit vs. inferred intent types
    - Confidence scoring based on model outputs
    - Integration with more sophisticated classification models
    """

    def __init__(self, config: dict | None = None):
        """
        Initialize the Intent Parser with optional configuration.

        Args:
            config: Optional dictionary containing configuration parameters
                   for the intent parser, such as confidence thresholds,
                   model settings, or feature flags.
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("IntentParser.__init__ START")
        self.config = config or {}
        self.logger = logger
        self.logger.info("IntentParser initialized with config: %s", self.config)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self.logger.info("IntentParser.__init__ END")

    def parse_intent(self, request: IntentRequest) -> IntentResponse:
        """
        Parse the intent from the incoming request.

        For MVP: Directly uses the provided request_type.
        Future: Will analyze the query text to infer intent.

        Args:
            request: The IntentRequest containing the query and request type.

        Returns:
            IntentResponse with the detected intent type, confidence score,
            and relevant metadata.
        """
        self.logger.info(
            "Processing intent request: query=%s, type=%s",
            request.query,
            request.request_type,
        )

        start_time = time.time()

        # For MVP: Deterministic approach - use the explicit request_type
        # This will be enhanced in the future with NLP-based intent detection
        detected_type = request.request_type

        # For MVP, we're 100% confident since we use the explicit type
        confidence = 1.0

        # Calculate processing time for metrics
        processing_time = time.time() - start_time

        # Create metadata for traceability and debugging
        metadata = {
            "processing_time": processing_time,
            "detection_method": "deterministic",  # Will be "nlp" or "hybrid" in future
        }

        # Add any configuration-specific metadata
        if self.config.get("include_config_in_metadata"):
            metadata["config"] = self.config

        self.logger.info(
            "Intent detected: %s (confidence: %.2f, time: %.4fs)",
            detected_type,
            confidence,
            processing_time,
        )

        # Construct and return the response
        return IntentResponse(
            detected_type=detected_type,
            explicit_type=request.request_type,  # Store the original explicit type
            inferred_type=None,  # Will be populated in future NLP implementation
            confidence=confidence,
            query=request.query,
            metadata=metadata,
        )

    def _keyword_based_classification(self, query: str) -> tuple[RequestType, float]:
        """
        Classify the intent based on keywords in the query.

        NOTE: This is a placeholder for future enhancement.
        Currently not used in the MVP but prepared for future implementation.

        Args:
            query: The user's query text to analyze.

        Returns:
            A tuple of (detected_type, confidence) based on keyword matching.
        """
        # This is a simple rule-based classifier that could be implemented in the future
        # It would look for specific keywords associated with each intent type

        query_lower = query.lower()

        # Rule generation keywords
        if any(
            kw in query_lower
            for kw in ["rule", "signature", "detection", "yara", "sigma", "tanium"]
        ):
            return RequestType.RULE_GENERATION, 0.8

        # Summarization keywords
        if any(kw in query_lower for kw in ["summarize", "summary", "recap", "tldr"]):
            return RequestType.SUMMARIZATION, 0.8

        # Enrichment keywords
        if any(
            kw in query_lower
            for kw in [
                "enrich",
                "additional",
                "more information",
                "context",
                "add details",
            ]
        ):
            return RequestType.ENRICHMENT, 0.7

        # Default to QUERY with lower confidence
        return RequestType.QUERY, 0.6

    # ======= Future NLP-based Intent Detection Methods =======

    def analyze_query_text(self, query: str) -> RequestType:
        """
        Analyze query text using NLP techniques to determine intent.

        Future Enhancement: This method will use NLP models or techniques to analyze
        the natural language query and classify it into one of the supported intent types.

        Args:
            query: The user's natural language query text.

        Returns:
            The inferred RequestType based on NLP analysis.
        """
        # Future implementation will include:
        # 1. Text preprocessing (tokenization, normalization, etc.)
        # 2. Feature extraction (embeddings, n-grams, etc.)
        # 3. Model inference using trained classifier
        # 4. Intent classification based on model output
        raise NotImplementedError("NLP-based query analysis not implemented yet")

    def calculate_confidence_score(self, query: str, detected_type: RequestType) -> float:
        """
        Calculate confidence score for the detected intent based on model outputs.

        Future Enhancement: This method will provide a confidence score for the
        intent detection based on model output probabilities or confidence metrics.

        Args:
            query: The user's natural language query text.
            detected_type: The detected RequestType to calculate confidence for.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        # Future implementation will include:
        # 1. Model probability extraction
        # 2. Confidence calibration
        # 3. Threshold adjustment based on intent type
        # 4. Context-aware confidence boosting
        raise NotImplementedError("Confidence calculation not implemented yet")

    def compare_intent_types(
        self, explicit_type: RequestType, inferred_type: RequestType
    ) -> tuple[RequestType, float]:
        """
        Compare explicitly provided intent type with inferred type from NLP analysis.

        Future Enhancement: This method will reconcile differences between the explicit
        type provided in the request and the type inferred through NLP analysis.

        Args:
            explicit_type: The RequestType explicitly provided in the request.
            inferred_type: The RequestType inferred through NLP analysis.

        Returns:
            A tuple of (final_type, confidence) based on the comparison.
        """
        # Future implementation will include:
        # 1. Conflict resolution strategy
        # 2. Confidence-based selection
        # 3. Potentially requestor role-based weighting
        # 4. Feedback mechanism for improving future detection
        raise NotImplementedError("Intent type comparison not implemented yet")

    def enhanced_intent_detection(self, request: IntentRequest) -> IntentResponse:
        """
        Perform enhanced intent detection using NLP and explicit type comparison.

        Future Enhancement: This method will combine explicit type information with
        NLP-based inference to provide more accurate intent detection with confidence scoring.

        Args:
            request: The IntentRequest containing the query and explicit request type.

        Returns:
            IntentResponse with detected type, confidence, and relevant metadata.
        """
        # Future implementation will include:
        # 1. NLP-based intent detection
        # 2. Comparison with explicit type
        # 3. Confidence calculation
        # 4. Enhanced metadata generation
        # 5. Logging of decision process

        # Placeholder implementation (actual implementation will be done in future sprints)
        start_time = time.time()

        # Get explicit type from request
        explicit_type = request.request_type

        # In the future, this will call analyze_query_text
        # For now, use keyword-based classification as a placeholder
        inferred_type, inferred_confidence = self._keyword_based_classification(request.query)

        # In the future, this will call compare_intent_types
        # For now, default to explicit type with high confidence
        if explicit_type == inferred_type:
            final_type = explicit_type
            confidence = 0.95  # High confidence when types match
        else:
            # For MVP, prioritize explicit type but with lower confidence
            final_type = explicit_type
            confidence = 0.7  # Lower confidence when types don't match

        processing_time = time.time() - start_time

        metadata = {
            "processing_time": processing_time,
            "detection_method": "hybrid",  # Using both explicit and inferred
            "explicit_type_confidence": 1.0,  # Explicit types always have max confidence
            "inferred_type_confidence": inferred_confidence,
        }

        return IntentResponse(
            detected_type=final_type,
            explicit_type=explicit_type,
            inferred_type=inferred_type,
            confidence=confidence,
            query=request.query,
            metadata=metadata,
        )
