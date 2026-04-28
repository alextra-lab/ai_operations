"""
Response Formatter for AI Operations Platform.

This module defines the ResponseFormatter class, which transforms LLM responses
into structured FormattedResponse objects with source citations, confidence
scoring, and suggested actions.

The Response Formatter is the final component in the orchestration workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → Tool & Model Router → LLM Router → Response Formatter
"""

import json
import re
from re import Pattern
from typing import Any

import yaml
from fastapi import HTTPException
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as json_validate

from shared.logging_utils.fastapi import configure_logging

from ..schemas.llm import LLMResponse
from ..schemas.response import (
    ConsolidatedMetrics,
    FormattedResponse,
    GuardMetrics,
    ModelMetrics,
    RetrievalMetrics,
    SourceMetadata,
)
from ..schemas.use_case_config import OutputContractConfig, OutputFormat, ValidationMode
from ..schemas.visualization_spec import VisualizationSpec  # noqa: TC001
from ..services.visualization_spec_generator import VisualizationSpecGenerator
from ..utils.cost_estimator import estimate_cost

logger = configure_logging(service_name="response_formatter", log_level="INFO", log_format="json")


class ResponseFormatter:
    """
    Transforms LLM outputs into structured FormattedResponse objects.

    This class extracts source citations, calculates confidence scores,
    and generates suggested actions from LLM outputs.
    """

    def __init__(
        self,
        source_extraction_patterns: list[Pattern] | None = None,
        confidence_threshold: float = 0.7,
        enable_suggested_actions: bool = True,
        **config: Any,
    ) -> None:
        """
        Initialize the ResponseFormatter with configuration options.

        Args:
            source_extraction_patterns: List of regex patterns for extracting sources,
                                        defaults to standard citation patterns if None
            confidence_threshold: Threshold for determining high confidence responses (0.0 to 1.0)
            enable_suggested_actions: Whether to generate suggested actions
            **config: Additional configuration options
        """
        self.confidence_threshold = confidence_threshold
        self.enable_suggested_actions = enable_suggested_actions
        self.config = config

        # Default source extraction patterns if none provided
        if source_extraction_patterns is None:
            self.source_extraction_patterns = [
                # Pattern for numbered references: [1] Document Title (doc_id)
                re.compile(r"\[(\d+)\]\s+([^(]+)\s+\(([^)]+)\)"),
                # Pattern for direct citations: Source: "Document Title" (doc_id)
                re.compile(r'Source:\s+"([^"]+)"\s+\(([^)]+)\)'),
                # Pattern for in-text citations: As mentioned in "Document Title" (doc_id)
                re.compile(r'mentioned in\s+"([^"]+)"\s+\(([^)]+)\)'),
                # Pattern for reference section: References:\n1. Document Title (doc_id)
                re.compile(r"^\d+\.\s+([^(]+)\s+\(([^)]+)\)", re.MULTILINE),
            ]
        else:
            self.source_extraction_patterns = source_extraction_patterns

        logger.info(
            "ResponseFormatter initialized with confidence_threshold=%f, "
            "enable_suggested_actions=%s, %d source patterns",
            confidence_threshold,
            enable_suggested_actions,
            len(self.source_extraction_patterns),
        )

    def _convert_context_sources(
        self, context_sources: list[dict[str, Any]]
    ) -> list[SourceMetadata]:
        """
        Convert context sources from retrieval to SourceMetadata objects.

        Args:
            context_sources: List of source dictionaries from retrieval context

        Returns:
            List of SourceMetadata objects
        """
        sources = []
        for source in context_sources:
            try:
                # Extract metadata
                meta = source.get("metadata", {})

                # Get chunk text from various possible fields
                chunk_text = (
                    source.get("content")
                    or source.get("snippet")
                    or source.get("text_snippet")
                    or meta.get("content")
                    or ""
                )

                source_metadata = SourceMetadata(
                    document_id=source.get("document_id", ""),
                    title=source.get("title", "Unknown Document"),
                    source=meta.get("source") or "Document Library",
                    author=meta.get("author"),
                    similarity_score=source.get("score", source.get("relevance_score", 0.0)),
                    page_number=meta.get("page_number"),
                    chunk_text=chunk_text,
                    content=chunk_text,
                    chunk_index=(
                        int(source.get("chunk_index"))  # type: ignore[arg-type]
                        if source.get("chunk_index") is not None
                        else (
                            int(meta.get("chunk_index"))  # type: ignore[arg-type]
                            if meta.get("chunk_index") is not None
                            else 0
                        )
                    ),
                    document_type=meta.get("document_type") or meta.get("file_type") or "text",
                    classification=meta.get("classification"),
                    created_at=meta.get("created_at") or "unknown",
                    url=source.get("url"),
                )
                sources.append(source_metadata)
            except Exception as e:
                logger.warning(
                    "Failed to convert source to SourceMetadata: %s",
                    type(e).__name__,
                    exc_info=True,
                )
                continue
        return sources

    def extract_sources(self, llm_output: str) -> list[SourceMetadata]:
        """
        Extract source citations from LLM output text.

        Uses regex patterns to identify and extract source information,
        creating SourceMetadata objects for each identified source.

        Args:
            llm_output: The raw text output from the LLM

        Returns:
            List of SourceMetadata objects representing the sources
        """
        logger.debug("Extracting sources from LLM output of length %d", len(llm_output))
        sources: list[SourceMetadata] = []
        source_ids_seen = set()

        # Look for source citations using all patterns
        for pattern in self.source_extraction_patterns:
            matches = pattern.findall(llm_output)

            if not matches:
                continue

            logger.debug("Found %d matches with pattern %s", len(matches), pattern.pattern)

            for match in matches:
                # Handle different match formats based on the regex pattern
                if len(match) == 3:  # Pattern with number, title, and ID: [1] Title (id)
                    _, title, doc_id = match
                elif len(match) == 2:  # Pattern with title and ID: Title (id)
                    title, doc_id = match
                else:
                    logger.warning("Unexpected match format (skipped)")
                    continue

                # Avoid duplicate sources
                if doc_id in source_ids_seen:
                    continue

                source_ids_seen.add(doc_id)

                # Extract content snippet (context around the citation)
                content_snippet = self._extract_content_snippet(llm_output, title, doc_id)

                # Calculate relevance score based on position and frequency
                relevance_score = self._calculate_relevance_score(llm_output, title, doc_id)

                # Determine source type based on document ID prefix or format
                # Note: source_type is determined but not used in current implementation
                _ = self._determine_source_type(doc_id)

                # Create source metadata
                source = SourceMetadata(
                    document_id=doc_id,
                    title=title.strip(),
                    source="LLM Output",
                    author=None,
                    similarity_score=relevance_score,
                    page_number=None,
                    chunk_text=content_snippet,
                    content=content_snippet,
                    chunk_index=0,
                    document_type="text",
                    classification=None,
                    created_at="",
                    url=None,
                )

                sources.append(source)

        logger.info("Extracted %d unique sources from LLM output", len(sources))
        return sources

    def _extract_content_snippet(self, text: str, title: str, doc_id: str) -> str:
        """
        Extract a relevant content snippet around the citation.

        Args:
            text: The full text to search in
            title: The title of the document
            doc_id: The document ID

        Returns:
            A snippet of text that represents the context of the citation
        """
        # Look for sentences containing the title or document ID
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if title in sentence or doc_id in sentence:
                return sentence.strip()

        # If no specific sentence found, return a default snippet
        return "Referenced in the response"

    def _calculate_relevance_score(self, text: str, title: str, doc_id: str) -> float:
        """
        Calculate a relevance score for the source based on frequency and position.

        Args:
            text: The full text to analyze
            title: The title of the document
            doc_id: The document ID

        Returns:
            A relevance score between 0.0 and 1.0
        """
        # Calculate metrics that affect relevance
        title_count = text.count(title)
        doc_id_count = text.count(doc_id)

        # Position factor - sources mentioned earlier are more relevant
        first_position = min(
            text.find(title) if title in text else len(text),
            text.find(doc_id) if doc_id in text else len(text),
        )
        position_factor = 1.0 - (first_position / len(text)) if len(text) > 0 else 0.5

        # Frequency factor - sources mentioned more frequently are more relevant
        frequency = title_count + doc_id_count
        frequency_factor = min(frequency / 5, 1.0)  # Cap at 1.0

        # Combined score with position weighted more heavily
        relevance_score = (position_factor * 0.6) + (frequency_factor * 0.4)

        # Ensure the score is within bounds
        return max(0.0, min(1.0, relevance_score))

    def _determine_source_type(self, doc_id: str) -> str:
        """
        Determine the source type based on the document ID format.

        Args:
            doc_id: The document ID

        Returns:
            A string representing the source type
        """
        # Common prefixes for different document types
        if doc_id.startswith("KB-"):
            return "KB"
        if doc_id.startswith("TI-"):
            return "threat intel"
        if doc_id.startswith("DOC-"):
            return "documentation"
        if doc_id.startswith("POL-"):
            return "policy"
        if doc_id.startswith("RULE-"):
            return "rule"
        return "reference"

    def format_response(
        self,
        text: str,
        sources: list[SourceMetadata],
        confidence: float,
        suggested_actions: dict | None = None,
        request_id: str | None = None,
        metrics: ConsolidatedMetrics | None = None,
        structured_data: dict[str, Any] | None = None,
        visualization_spec: Any | None = None,
    ) -> FormattedResponse:
        """
        Structure the response with text, sources, confidence, metrics, and suggested actions.

        Always returns a complete response with all metrics present. If metrics are not provided,
        default metrics are created following the Null Object Pattern.

        Args:
            text: The processed response text
            sources: List of extracted source metadata
            confidence: Overall confidence score
            suggested_actions: Optional dictionary of suggested next actions
            request_id: Unique identifier for this request execution
            metrics: Optional comprehensive metrics from all components
            structured_data: Optional parsed structured output (JSON/YAML/structured format)
            visualization_spec: Optional Vega-Lite visualization spec (ADR-068)

        Returns:
            A FormattedResponse object with comprehensive metrics
        """
        logger.debug(
            "Formatting response with %d sources and confidence %f",
            len(sources),
            confidence,
        )

        # Clean up the response text (remove raw citations if they exist at the end)
        cleaned_text = self._clean_response_text(text)

        # If no metrics provided, create default ones
        if metrics is None:
            from ..schemas.response import (
                ConsolidatedMetrics,
                GuardMetrics,
                ModelMetrics,
                RetrievalMetrics,
                ServiceStatus,
            )

            metrics = ConsolidatedMetrics(
                retrieval=RetrievalMetrics(
                    top_k=0,
                    hits=0,
                    avg_similarity=0.0,
                    min_similarity=0.0,
                    max_similarity=0.0,
                    source_count=len(sources),
                ),
                guard=GuardMetrics(risk_score=0.0, modified=False, details={}),
                model=ModelMetrics(
                    model_id="unknown",
                    tokens_in=0,
                    tokens_out=0,
                    total_tokens=0,
                    processing_time=0.0,
                    metadata={},
                ),
                confidence_score=confidence,
                service_status=ServiceStatus(
                    retrieval_active=False,
                    guard_active=False,
                    model_active=False,
                    embedding_active=False,
                    retrieval_healthy=True,
                    guard_healthy=True,
                    model_healthy=True,
                ),
            )

        # Create the formatted response
        formatted_response = FormattedResponse(
            response=cleaned_text,
            sources=sources,
            confidence=confidence,
            metrics=metrics,
            suggested_actions=suggested_actions or {},
            request_id=request_id or "unknown",
            cache_stats=None,
            structured_data=structured_data,
            visualization_spec=visualization_spec,
        )

        logger.info(
            "Formatted response created with %d characters, %d sources, "
            "confidence: %f, has_suggested_actions: %s",
            len(cleaned_text),
            len(sources),
            confidence,
            suggested_actions is not None,
        )

        return formatted_response

    def _clean_response_text(self, text: str) -> str:
        """
        Clean the response text by removing reference sections and raw citations.

        Args:
            text: The raw text to clean

        Returns:
            Cleaned text without reference sections
        """
        # Remove "References:" section if present
        ref_section_pattern = re.compile(r"\n+References:[\s\S]*$", re.IGNORECASE)
        cleaned = ref_section_pattern.sub("", text)

        # Remove "Sources:" section if present
        sources_section_pattern = re.compile(r"\n+Sources:[\s\S]*$", re.IGNORECASE)
        cleaned = sources_section_pattern.sub("", cleaned)

        # Remove numbered citations like [1], [2] if at the end of sentences
        citation_pattern = re.compile(r"\s+\[\d+\]\.?")
        cleaned = citation_pattern.sub(".", cleaned)

        # Strip extra whitespace
        return cleaned.strip()

    def _calculate_confidence(
        self, llm_response: LLMResponse, sources: list[SourceMetadata]
    ) -> float:
        """
        Calculate an overall confidence score based on LLM response and sources.

        Args:
            llm_response: The LLM response object
            sources: The extracted sources

        Returns:
            A confidence score between 0.0 and 1.0
        """
        # Base confidence from metadata if available
        base_confidence = (
            llm_response.metadata.get("confidence", 0.5)
            if hasattr(llm_response, "metadata") and llm_response.metadata
            else 0.5
        )

        # Source-based factors
        source_count = len(sources)

        # More sources generally means higher confidence, up to a point
        if source_count == 0:
            source_factor = 0.0
        elif source_count == 1:
            source_factor = 0.3
        elif source_count == 2:
            source_factor = 0.6
        else:
            source_factor = 0.8  # Diminishing returns after 3+ sources

        # Average relevance of sources
        avg_relevance = (
            sum(source.similarity_score for source in sources) / source_count
            if source_count > 0
            else 0.0
        )

        # Processing time factor - faster responses might indicate higher confidence
        # But only small effect
        processing_time = (
            llm_response.processing_time if hasattr(llm_response, "processing_time") else 1.0
        )
        time_factor = max(0.0, min(0.1, 2.0 / processing_time)) if processing_time > 0 else 0.0

        # Combine factors with appropriate weights
        confidence = (
            (base_confidence * 0.5)  # Base model confidence
            + (source_factor * 0.3)  # Source count factor
            + (avg_relevance * 0.15)  # Source relevance factor
            + (time_factor * 0.05)  # Processing time factor
        )

        # Ensure the confidence is within bounds
        return float(max(0.0, min(1.0, confidence)))

    def _generate_suggested_actions(
        self, response_text: str, sources: list[SourceMetadata], confidence: float
    ) -> dict[str, Any] | None:
        """
        Generate suggested actions based on the response content and confidence.

        Args:
            response_text: The response text
            sources: The extracted sources
            confidence: The overall confidence score

        Returns:
            Dictionary of suggested actions or None if disabled
        """
        if not self.enable_suggested_actions:
            return None

        suggested_actions = {}

        # Suggest viewing sources if available
        if sources:
            suggested_actions["view_sources"] = {
                "label": "View Source Documents",
                "documents": [{"id": s.document_id, "title": s.title} for s in sources],
            }

        # Suggest more specific query if confidence is low
        if confidence < self.confidence_threshold:
            suggested_actions["refine_query"] = {
                "label": "Refine Your Query",
                "reason": "The answer may not be comprehensive enough.",
            }

        # Detect if the response mentions threat intelligence
        if any(s.source == "threat intel" for s in sources) or "threat" in response_text.lower():
            suggested_actions["investigate_threat"] = {
                "label": "Investigate Related Threats",
                "threat_types": self._extract_threat_types(response_text),
            }

        # Return None if no actions were added
        return suggested_actions if suggested_actions else None

    def _extract_threat_types(self, text: str) -> list[str]:
        """
        Extract mentioned threat types from the response text.

        Args:
            text: The response text

        Returns:
            List of identified threat types
        """
        threat_types = []

        # Look for common threat pattern mentions
        threat_patterns = [
            (
                r'malware(?:\s+named\s+|\s+called\s+|\s+known\s+as\s+)["\']([\w\s-]+)[\'"]',
                "malware",
            ),
            (
                r'ransomware(?:\s+named\s+|\s+called\s+|\s+known\s+as\s+)["\']([\w\s-]+)[\'"]',
                "ransomware",
            ),
            (
                r'exploit(?:\s+targeting\s+|\s+for\s+|\s+in\s+)["\']([\w\s-]+)[\'"]',
                "exploit",
            ),
            (r"vulnerability\s+(?:CVE-[\d-]+)", "vulnerability"),
            (r"(?:APT|advanced\s+persistent\s+threat)[\s-]+(\d+|[a-zA-Z]+)", "apt"),
        ]

        for pattern, threat_type in threat_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                threat_types.append(threat_type)

        # Deduplicate
        return list(set(threat_types)) if threat_types else []

    def _parse_security_flags(self, guard_details: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and enhance security flags from guard details.

        Extracts key security indicators aligned with actual LLM Guard scanners:
        - anonymize: PII detection/anonymization
        - prompt_injection: Jailbreak/prompt injection attempts
        - secrets: API keys, passwords, tokens
        - gibberish: Gibberish/nonsense detection
        - language: Language validation
        - regex: Pattern matching for credentials

        Args:
            guard_details: Raw guard details from LLM-Guard

        Returns:
            Enhanced details dictionary with parsed security flags
        """
        enhanced_details = dict(guard_details)

        # Parse scanner results if available
        if "scanners" in guard_details:
            scanners = guard_details["scanners"]

            # PII Detection (anonymize scanner)
            enhanced_details["pii_detected"] = self._check_scanner_flag(scanners, ["anonymize"])

            # Jailbreak/Prompt Injection Detection
            enhanced_details["jailbreak_attempt"] = self._check_scanner_flag(
                scanners, ["prompt_injection"]
            )

            # Secrets Detection (API keys, passwords, tokens)
            enhanced_details["secrets_detected"] = self._check_scanner_flag(
                scanners, ["secrets", "regex"]
            )

            # Gibberish Detection
            enhanced_details["gibberish_detected"] = self._check_scanner_flag(
                scanners, ["gibberish"]
            )

            # Language Validation (invalid language)
            enhanced_details["invalid_language"] = self._check_scanner_flag(scanners, ["language"])

            # Content Filtering - aggregate of any failed scanner
            enhanced_details["content_filtered"] = any(
                [
                    enhanced_details.get("pii_detected", False),
                    enhanced_details.get("jailbreak_attempt", False),
                    enhanced_details.get("secrets_detected", False),
                    enhanced_details.get("gibberish_detected", False),
                    enhanced_details.get("invalid_language", False),
                ]
            )

            # Legacy toxicity flag (not implemented in current LLM Guard)
            # Kept for backward compatibility
            enhanced_details["toxicity_detected"] = False

            # Collect blocked/failed scanners
            blocked_categories = []
            for scanner_name, scanner_result in scanners.items():
                if isinstance(scanner_result, dict):
                    # Check if scanner failed (not passed or high risk score)
                    failed = (
                        scanner_result.get("passed") is False
                        or scanner_result.get("score", 0) > 0.5
                    )
                    if failed:
                        blocked_categories.append(scanner_name)
                    # Extract specific categories if available
                    if "blocked_categories" in scanner_result:
                        blocked_categories.extend(scanner_result["blocked_categories"])

            if blocked_categories:
                enhanced_details["blocked_categories"] = list(set(blocked_categories))

        # Ensure flags exist even if scanners not available
        enhanced_details.setdefault("pii_detected", False)
        enhanced_details.setdefault("toxicity_detected", False)  # Legacy
        enhanced_details.setdefault("jailbreak_attempt", False)
        enhanced_details.setdefault("secrets_detected", False)
        enhanced_details.setdefault("gibberish_detected", False)
        enhanced_details.setdefault("invalid_language", False)
        enhanced_details.setdefault("content_filtered", False)
        enhanced_details.setdefault("blocked_categories", [])

        return enhanced_details

    def _check_scanner_flag(self, scanners: dict[str, Any], scanner_keywords: list[str]) -> bool:
        """
        Check if any scanner matching keywords indicates a security issue.

        Checks for actual LLM Guard result format:
        - {"passed": False, "score": float}  # Scanner failed
        - {"passed": True, "score": float}   # Scanner passed

        Legacy formats also supported:
        - {"blocked": True}
        - {"sanitized": True}
        - {"detected": True}
        - {"risk_score": float > 0.5}

        Args:
            scanners: Dictionary of scanner results
            scanner_keywords: List of keywords to match scanner names

        Returns:
            True if any matching scanner detected an issue
        """
        for scanner_name, scanner_result in scanners.items():
            # Check if scanner name matches any keyword
            if any(keyword in scanner_name.lower() for keyword in scanner_keywords):
                # Check various result formats
                if isinstance(scanner_result, dict):
                    # PRIMARY FORMAT: Check LLM Guard "passed" field (actual format)
                    if scanner_result.get("passed") is False:
                        return True

                    # PRIMARY FORMAT: Check LLM Guard "score" field (actual format)
                    score = scanner_result.get("score", 0.0)
                    if score > 0.5:
                        return True

                    # LEGACY FORMATS: Check for blocked/sanitized flags
                    if scanner_result.get("blocked") or scanner_result.get("sanitized"):
                        return True
                    # Check for detection flag
                    if scanner_result.get("detected"):
                        return True
                    # Check risk_score threshold
                    risk_score = scanner_result.get("risk_score", 0.0)
                    if risk_score > 0.5:
                        return True
                elif isinstance(scanner_result, bool) and scanner_result:
                    return True

        return False

    async def _consolidate_metrics(
        self,
        llm_response: LLMResponse,
        sources: list[SourceMetadata],
        retrieval_metrics: dict[str, Any] | None = None,
        guard_metrics: dict[str, Any] | None = None,
        retrieval_attempted: bool = True,
        guard_attempted: bool = True,
    ) -> ConsolidatedMetrics:
        """
        Consolidate metrics from all services into a unified metrics object.

        ALWAYS returns a complete ConsolidatedMetrics object following the
        Null Object Pattern. When services are disabled or unavailable,
        safe default values are used instead of returning None.

        This ensures:
        - Frontend never encounters null metrics
        - UI displays gracefully regardless of service availability
        - System behavior is consistent and predictable
        - Operators can see which services were actually used

        Args:
            llm_response: The LLM response containing model metrics
            sources: List of sources used in the response
            retrieval_metrics: Optional retrieval metrics data (None if not used)
            guard_metrics: Optional guard metrics data (None if not used)
            retrieval_attempted: Whether retrieval was attempted (False if disabled)
            guard_attempted: Whether guard was attempted (False if disabled)

        Returns:
            ConsolidatedMetrics with all sub-metrics always present
        """
        # === RETRIEVAL METRICS ===
        if retrieval_metrics and retrieval_attempted:
            # Service was used and returned metrics
            similarity_scores = retrieval_metrics.get("similarity_scores", [])
            avg_similarity = (
                sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            )
            min_similarity = min(similarity_scores) if similarity_scores else 0.0
            max_similarity = max(similarity_scores) if similarity_scores else 0.0

            retrieval = RetrievalMetrics(
                top_k=retrieval_metrics.get("top_k", 0),
                hits=retrieval_metrics.get("hits", 0),
                avg_similarity=avg_similarity,
                min_similarity=min_similarity,
                max_similarity=max_similarity,
                source_count=len(sources),
            )
            retrieval_active = True
            retrieval_healthy = True
            logger.debug(
                f"Retrieval metrics collected: {retrieval.hits} hits, "
                f"avg similarity: {retrieval.avg_similarity:.2f}"
            )
        elif retrieval_attempted and not retrieval_metrics:
            # Service was attempted but failed
            retrieval = RetrievalMetrics(
                top_k=0,
                hits=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                source_count=0,
            )
            retrieval_active = False
            retrieval_healthy = False
            logger.warning("Retrieval was attempted but returned no metrics")
        else:
            # Service was not attempted (disabled or not needed)
            retrieval = RetrievalMetrics(
                top_k=0,
                hits=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                source_count=0,
            )
            retrieval_active = False
            retrieval_healthy = True  # Healthy, just not used
            logger.debug("Retrieval not attempted (disabled or not needed)")

        # === GUARD METRICS ===
        if guard_metrics and guard_attempted:
            # Service was used and returned metrics
            guard_details = guard_metrics.get("details", {})
            enhanced_details = self._parse_security_flags(guard_details)

            guard = GuardMetrics(
                risk_score=guard_metrics.get("risk_score", 0.0),
                modified=guard_metrics.get("modified", False),
                details=enhanced_details,
            )
            guard_active = True
            guard_healthy = True
            logger.debug(
                f"Guard metrics collected: risk={guard.risk_score:.2f}, modified={guard.modified}"
            )
        elif guard_attempted and not guard_metrics:
            # Service was attempted but failed
            guard = GuardMetrics(
                risk_score=0.0,
                modified=False,
                details={
                    "status": "failed",
                    "reason": "guard_service_unavailable",
                    "message": "LLM-Guard validation failed - proceeding without validation",
                },
            )
            guard_active = False
            guard_healthy = False
            logger.warning("Guard was attempted but returned no metrics")
        else:
            # Service was not attempted (disabled)
            guard = GuardMetrics(
                risk_score=0.0,
                modified=False,
                details={
                    "status": "not_performed",
                    "reason": "guard_disabled",
                    "message": "LLM-Guard validation is disabled in this environment",
                },
            )
            guard_active = False
            guard_healthy = True  # Healthy, just disabled
            logger.debug("Guard not attempted (disabled)")

        # === MODEL METRICS ===
        # Model metrics are always present if we got an LLM response
        # NOTE: LLM router stores tokens as "prompt_tokens" and "completion_tokens"
        tokens_in = llm_response.metadata.get("prompt_tokens", 0)
        tokens_out = llm_response.metadata.get("completion_tokens", llm_response.tokens_used)

        # Get actual model ID - check metadata first, fallback to enum string
        # NOTE: The actual model ID (gpt-4o-mini, claude-3-5-sonnet, etc.) should be
        # stored in metadata["model_id"]. If not present, we fallback to the ModelType
        # enum string (QUERY, RULE_GENERATION, etc.) which is less accurate for cost estimation.
        model_id = llm_response.metadata.get("model_id", str(llm_response.model_used))

        # Calculate cost estimate
        # TODO: Convert format_response to async when Orchestrator is converted (Phase 5)
        # Calculate cost using async estimate_cost function
        cost_info = await estimate_cost(model_id, tokens_in, tokens_out)

        # Enhance metadata with cost, timing, and model parameters
        enhanced_metadata = dict(llm_response.metadata)
        # Store actual model_id in metadata for frontend display
        # This allows frontend to distinguish between actual model ID and ModelType enum
        enhanced_metadata["model_id"] = model_id
        enhanced_metadata["cost_estimate"] = cost_info["total_cost"]
        enhanced_metadata["cost_breakdown"] = cost_info

        # Add model parameters if available in metadata
        if "temperature" in enhanced_metadata:
            enhanced_metadata["parameters"] = {
                "temperature": enhanced_metadata.get("temperature"),
                "max_tokens": enhanced_metadata.get("max_tokens"),
                "top_p": enhanced_metadata.get("top_p"),
                "top_k": enhanced_metadata.get("top_k"),
            }

        # Add timing breakdown if available
        if "timing" in enhanced_metadata:
            enhanced_metadata["timing_breakdown"] = enhanced_metadata["timing"]

        model = ModelMetrics(
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            total_tokens=llm_response.tokens_used,
            processing_time=llm_response.processing_time,
            metadata=enhanced_metadata,
        )
        model_active = True
        model_healthy = True

        # === SERVICE STATUS ===
        from ..schemas.response import ServiceStatus

        service_status = ServiceStatus(
            retrieval_active=retrieval_active,
            guard_active=guard_active,
            model_active=model_active,
            embedding_active=retrieval_active,  # Embedding used when retrieval used
            retrieval_healthy=retrieval_healthy,
            guard_healthy=guard_healthy,
            model_healthy=model_healthy,
        )

        # === CONFIDENCE CALCULATION ===
        # Calculate consolidated confidence accounting for missing services
        confidence_score = self._calculate_consolidated_confidence(retrieval, guard, model, sources)

        logger.info(
            "Metrics consolidated",
            extra={
                "retrieval_active": retrieval_active,
                "guard_active": guard_active,
                "model_active": model_active,
                "confidence": confidence_score,
            },
        )

        return ConsolidatedMetrics(
            retrieval=retrieval,
            guard=guard,
            model=model,
            confidence_score=confidence_score,
            calculation_method="weighted_consolidation",
            service_status=service_status,
        )

    def _calculate_consolidated_confidence(
        self,
        retrieval: RetrievalMetrics | None,
        guard: GuardMetrics | None,
        model: ModelMetrics,  # Keep for future use
        sources: list[SourceMetadata],
    ) -> float:
        """
        Calculate consolidated confidence score using weighted factors.

        Formula:
        - 40% retrieval (avg_similarity)
        - 20% source (citation count)
        - 20% model (model quality)
        - 10% guard (inverse risk)
        - 10% success (LLM completion)

        Args:
            retrieval: Optional retrieval metrics
            guard: Optional guard metrics
            model: Model metrics
            sources: List of sources

        Returns:
            Consolidated confidence score (0.0 to 1.0)
        """
        # Base score from LLM completion (10%)
        base_score = 0.1  # LLM completed successfully

        # Retrieval component (40%)
        retrieval_score = 0.0
        if retrieval and retrieval.avg_similarity > 0:
            retrieval_score = retrieval.avg_similarity * 0.4

        # Source component (20%)
        source_score = min(len(sources) / 5.0, 1.0) * 0.2  # Normalize to 5 sources max

        # Model component (20%)
        model_score = 0.2  # Model completed successfully
        # Future: Could factor in model quality, token efficiency, etc.
        _ = model  # Acknowledge parameter usage

        # Guard component (10%)
        guard_score = 0.1
        if guard:
            # Inverse risk score (lower risk = higher confidence)
            guard_score = (1.0 - guard.risk_score) * 0.1

        # Calculate final consolidated score
        consolidated_score = base_score + retrieval_score + source_score + model_score + guard_score

        # Ensure score is within bounds
        return max(0.0, min(1.0, consolidated_score))

    def validate_output(
        self, response_text: str, output_contract: OutputContractConfig | None
    ) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        """
        Validate output against the configured output contract.

        Supports best-effort and strict validation modes for text, JSON, and YAML formats.
        Returns parsed structured_data when format is JSON, YAML, or STRUCTURED.

        Args:
            response_text: The raw response text from the LLM
            output_contract: The output contract configuration

        Returns:
            Tuple of (validated_text, validation_metadata, structured_data or None)

        Raises:
            HTTPException: If validation fails in strict mode
        """
        if not output_contract:
            return response_text, {"validation_applied": False}, None

        validation_metadata: dict[str, Any] = {
            "validation_applied": True,
            "format": output_contract.format.value,
            "validation_mode": output_contract.validation_mode.value,
            "errors": [],
            "warnings": [],
        }

        logger.info(
            f"Validating output against contract: format={output_contract.format.value}, "
            f"mode={output_contract.validation_mode.value}"
        )

        # TEXT format validation
        if output_contract.format == OutputFormat.TEXT:
            if not isinstance(response_text, str):
                validation_metadata["errors"].append("Output is not a string")
                if output_contract.validation_mode == ValidationMode.STRICT:
                    raise HTTPException(
                        status_code=422,
                        detail="Output validation failed: expected text format",
                    )
            return response_text, validation_metadata, None

        # JSON format validation
        if output_contract.format == OutputFormat.JSON:
            return self._validate_json_output(response_text, output_contract, validation_metadata)

        # YAML format validation
        if output_contract.format == OutputFormat.YAML:
            return self._validate_yaml_output(response_text, output_contract, validation_metadata)

        # STRUCTURED format
        if output_contract.format == OutputFormat.STRUCTURED:
            try:
                return self._validate_json_output(
                    response_text, output_contract, validation_metadata
                )
            except Exception:
                try:
                    return self._validate_yaml_output(
                        response_text, output_contract, validation_metadata
                    )
                except Exception as e:
                    err_list = validation_metadata.get("errors", [])
                    if isinstance(err_list, list):
                        err_list.append(f"Could not parse as JSON or YAML: {e!s}")
                    else:
                        validation_metadata["errors"] = [f"Could not parse as JSON or YAML: {e!s}"]
                    if output_contract.validation_mode == ValidationMode.STRICT:
                        raise HTTPException(
                            status_code=422,
                            detail="Output validation failed: could not parse structured format",
                        )
                    return response_text, validation_metadata, None

        validation_metadata["warnings"].append(f"Unknown format: {output_contract.format}")
        return response_text, validation_metadata, None

    def _validate_json_output(
        self,
        response_text: str,
        output_contract: OutputContractConfig,
        validation_metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        """Validate JSON output format and schema; return (text, metadata, structured_data)."""
        try:
            parsed_json = json.loads(response_text)
            validation_metadata["parsed"] = True

            if output_contract.output_schema:
                try:
                    json_validate(instance=parsed_json, schema=output_contract.output_schema)
                    validation_metadata["schema_valid"] = True
                    logger.info("JSON output validated successfully against schema")
                except JsonSchemaValidationError as e:
                    validation_metadata["schema_valid"] = False
                    error_msg = f"JSON schema validation failed: {e!s}"
                    validation_metadata["errors"].append(error_msg)
                    logger.warning(error_msg)

                    if output_contract.validation_mode == ValidationMode.STRICT:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Output validation failed: {error_msg}",
                        )

            return json.dumps(parsed_json, indent=2), validation_metadata, parsed_json

        except json.JSONDecodeError as e:
            validation_metadata["parsed"] = False
            error_msg = f"Invalid JSON: {e!s}"
            validation_metadata["errors"].append(error_msg)
            logger.warning(error_msg)

            if output_contract.validation_mode == ValidationMode.STRICT:
                raise HTTPException(
                    status_code=422, detail=f"Output validation failed: {error_msg}"
                )

            return response_text, validation_metadata, None

    def _validate_yaml_output(
        self,
        response_text: str,
        output_contract: OutputContractConfig,
        validation_metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        """Validate YAML output format; return (text, metadata, structured_data)."""
        try:
            parsed_yaml = yaml.safe_load(response_text)
            validation_metadata["parsed"] = True

            if output_contract.output_schema:
                try:
                    json_validate(instance=parsed_yaml, schema=output_contract.output_schema)
                    validation_metadata["schema_valid"] = True
                    logger.info("YAML output validated successfully against schema")
                except JsonSchemaValidationError as e:
                    validation_metadata["schema_valid"] = False
                    error_msg = f"YAML schema validation failed: {e!s}"
                    validation_metadata["errors"].append(error_msg)
                    logger.warning(error_msg)

                    if output_contract.validation_mode == ValidationMode.STRICT:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Output validation failed: {error_msg}",
                        )

            return (
                yaml.dump(parsed_yaml, default_flow_style=False),
                validation_metadata,
                parsed_yaml if isinstance(parsed_yaml, dict) else None,
            )

        except yaml.YAMLError as e:
            validation_metadata["parsed"] = False
            error_msg = f"Invalid YAML: {e!s}"
            validation_metadata["errors"].append(error_msg)
            logger.warning(error_msg)

            if output_contract.validation_mode == ValidationMode.STRICT:
                raise HTTPException(
                    status_code=422, detail=f"Output validation failed: {error_msg}"
                )

            return response_text, validation_metadata, None

    async def process(
        self,
        llm_response: LLMResponse,
        request_id: str | None = None,
        retrieval_metrics: dict[str, Any] | None = None,
        guard_metrics: dict[str, Any] | None = None,
        output_contract: OutputContractConfig | None = None,
        context_sources: list[dict[str, Any]] | None = None,
        retrieval_attempted: bool = True,
        guard_attempted: bool = True,
    ) -> FormattedResponse:
        """
        Process an LLM response into a structured FormattedResponse with comprehensive metrics.

        Always returns a complete response with all metrics present, even if
        services were disabled or unavailable.

        This is the main method that coordinates source extraction, confidence
        calculation, suggested action generation, metrics consolidation, and response formatting.

        Args:
            llm_response: The LLMResponse object from the LLM Router
            request_id: Unique identifier for this request execution
            retrieval_metrics: Optional retrieval metrics data (None if not used)
            guard_metrics: Optional guard metrics data (None if not used)
            output_contract: Optional output contract configuration for validation
            context_sources: Optional list of source documents from retrieval context
            retrieval_attempted: Whether retrieval was attempted (False if disabled)
            guard_attempted: Whether guard was attempted (False if disabled)

        Returns:
            A FormattedResponse with all metrics always present
        """
        logger.info(
            "Processing LLM response for formatting (model: %s, tokens: %d)",
            (llm_response.model_used if hasattr(llm_response, "model_used") else "unknown"),
            llm_response.tokens_used if hasattr(llm_response, "tokens_used") else 0,
        )

        # Extract the raw text from the LLM response
        response_text = llm_response.response

        # Validate output against contract if provided; capture structured_data when present
        validation_metadata: dict[str, Any] = {}
        structured_data: dict[str, Any] | None = None
        if output_contract and response_text is not None:
            response_text, validation_metadata, structured_data = self.validate_output(
                response_text, output_contract
            )
            logger.info(
                f"Output validation completed: errors={len(validation_metadata.get('errors', []))}, "
                f"warnings={len(validation_metadata.get('warnings', []))}, "
                f"has_structured_data={structured_data is not None}"
            )

        # Use context sources if provided, otherwise extract from LLM output
        if context_sources:
            # Convert context sources to SourceMetadata objects
            sources = self._convert_context_sources(context_sources)
            logger.info(f"Using {len(sources)} sources from retrieval context")
        else:
            # Fallback: Extract sources from the LLM output (legacy behavior)
            sources = (
                self.extract_sources(response_text)
                if (response_text is not None and response_text)
                else []
            )
            logger.info(f"Extracted {len(sources)} sources from LLM output")

        # Calculate the confidence score
        confidence = self._calculate_confidence(llm_response, sources)

        # Consolidate comprehensive metrics - ALWAYS returns complete object
        consolidated_metrics = await self._consolidate_metrics(
            llm_response,
            sources,
            retrieval_metrics,
            guard_metrics,
            retrieval_attempted=retrieval_attempted,
            guard_attempted=guard_attempted,
        )

        # Add validation metadata to metrics if present
        if validation_metadata and consolidated_metrics.model:
            consolidated_metrics.model.metadata["output_validation"] = validation_metadata

        # Generate suggested actions
        safe_response_text = response_text or ""
        suggested_actions = self._generate_suggested_actions(
            safe_response_text, sources, confidence
        )

        # Generate portable visualization spec (ADR-068) when
        # template_id and structured_data are both present
        viz_spec: VisualizationSpec | None = None
        if structured_data and output_contract and output_contract.template_id:
            try:
                viz_gen = VisualizationSpecGenerator()
                # Build a minimal template dict from the contract
                # The full template definition is frontend-side; here we
                # accept template_definition passed via output_contract
                template_def = getattr(output_contract, "template_definition", None)
                if template_def and isinstance(template_def, dict):
                    viz_spec = viz_gen.generate(template_def, structured_data)
                    logger.info(
                        "Generated visualization spec with %d sections",
                        len(viz_spec.sections),
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to generate visualization spec: %s",
                    str(exc),
                )

        # Format the response with metrics and optional structured_data
        formatted_response = self.format_response(
            safe_response_text,
            sources,
            confidence,
            suggested_actions,
            request_id,
            consolidated_metrics,
            structured_data=structured_data,
            visualization_spec=viz_spec,
        )

        logger.info(
            "LLM response processed successfully with confidence %f and comprehensive metrics",
            confidence,
        )

        return formatted_response
