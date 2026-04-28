"""
Intent Parser Schema for AI Operations Platform.

This module defines the schema models for the Intent Parser component,
which classifies incoming requests into specific types for appropriate routing
in the orchestrator.

For MVP: Intent determination is deterministic based on explicit parameters provided by
the UI or Automation Source (SOAR playbook).

Future: Will add NLP-based intent detection to run in parallel with explicit parameters
for validation and eventual transition to fully automated intent detection.
"""

from enum import Enum

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """
    Enumeration of supported request types.

    These types categorize the different kinds of processing the orchestrator can perform,
    allowing for appropriate routing and handling of requests.

    Synced with database intent_types table (ADR-069).
    """

    # Original system intents
    QUERY = "QUERY"  # General questions and information retrieval
    RULE_GENERATION = (
        "RULE_GENERATION"  # Creation of detection rules (Lucene/KQL, Tanium EDR, Yara)
    )
    SUMMARIZATION = "SUMMARIZATION"  # Summarization of document content or incident data
    ENRICHMENT = "ENRICHMENT"  # Enrichment of incidents with threat intelligence

    # Extended system intents (added per migration 036)
    CLASSIFICATION = "CLASSIFICATION"  # Categorization and labeling
    EXTRACTION = "EXTRACTION"  # Structured data extraction from unstructured content
    GENERATION = "GENERATION"  # Content or artifact generation
    ANALYSIS = "ANALYSIS"  # Deep analysis and assessment
    THREAT_TRIAGE = "THREAT_TRIAGE"  # Threat assessment and prioritization
    CONTRACT_REVIEW = "CONTRACT_REVIEW"  # Contract analysis and key terms extraction
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"  # Regulatory compliance verification


class IntentRequest(BaseModel):
    """
    Model for incoming intent requests.

    For MVP: The request_type is required and used deterministically.
    Future: The request_type will remain for backward compatibility,
            but may also be inferred from the query text.
    """

    query: str = Field(
        ..., description="The user's natural language input or query text", min_length=1
    )
    request_type: RequestType = Field(
        ..., description="Type of request (required for MVP, may be optional in future)"
    )
    context: dict | None = Field(
        None, description="Additional context information to aid processing"
    )


class IntentResponse(BaseModel):
    """
    Model for intent detection response.

    For MVP: The detected_type will be the same as the explicitly provided request_type,
             and confidence will be 1.0.
    Future: Will include both explicit and inferred types with calculated confidence scores.
    """

    model_config = {"arbitrary_types_allowed": True}

    detected_type: RequestType = Field(
        ...,
        description="The final determined request type (matches explicit_type for MVP)",
    )
    explicit_type: RequestType | None = Field(
        None, description="The request type explicitly provided in the request"
    )
    inferred_type: RequestType | None = Field(
        None,
        description="The request type inferred through NLP analysis (future implementation)",
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the detection (1.0 for MVP's deterministic approach)",
        ge=0.0,
        le=1.0,
    )
    query: str = Field(..., description="Original or reformulated query", min_length=1)
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the intent detection process",
    )
