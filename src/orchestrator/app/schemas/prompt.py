"""
Prompt Assembler Schema for AI Operations Platform.

This module defines the schema models for the Prompt Assembler component,
which loads appropriate templates and context based on the intent type
to create properly formatted prompts for the LLM.

The Prompt Assembler is a key component in the orchestrator workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → Tool & Model Router → LLM Router → Response Formatter
"""

from pydantic import BaseModel, Field, field_validator, model_validator

from shared.logging_utils.fastapi import configure_logging

from .intent import IntentResponse

# Configure logger for this schema module
logger = configure_logging(service_name="prompt_schema")


class PromptTemplate(BaseModel):
    """
    Model for prompt templates.

    Defines the structure and required variables for prompt templates that can be
    filled with specific content to create prompts for different types of requests.
    Templates contain placeholders (e.g., {query}, {context}) that will be replaced
    with actual values during prompt assembly.
    """

    template_id: str = Field(..., description="Unique identifier for the template", min_length=1)
    template: str = Field(
        ...,
        description="The actual template with placeholders (e.g., {query}, {context})",
        min_length=1,
    )
    variables: list[str] = Field(
        ..., description="Required variables that must be provided to fill the template"
    )

    @field_validator("variables")
    @classmethod
    def validate_variables_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that the variables list is not empty."""
        if not v:
            logger.error("PromptTemplate validation failed: variables list is empty")
            raise ValueError("At least one variable must be defined")
        logger.debug("PromptTemplate variables validated")
        return v

    @model_validator(mode="after")
    def check_template_variables(self) -> "PromptTemplate":
        for var in self.variables:
            placeholder = f"{{{var}}}"
            if placeholder not in self.template:
                logger.error(
                    f"PromptTemplate validation failed: Template missing placeholder for variable: {placeholder}"
                )
                raise ValueError(
                    f"Template must contain placeholder for declared variable: {placeholder}"
                )
        logger.debug("PromptTemplate template validated")
        return self


class PromptRequest(BaseModel):
    """
    Model for prompt assembly requests.

    Contains the processed intent from the Intent Parser and additional context
    (e.g., retrieved documents from the Retrieval Engine) needed to assemble
    a complete prompt.
    """

    model_config = {"arbitrary_types_allowed": True}

    intent: IntentResponse = Field(..., description="The processed intent from the Intent Parser")
    context: dict | None = Field(
        None,
        description="Additional context (e.g., retrieved documents, user information)",
    )


class PromptResponse(BaseModel):
    """
    Model for assembled prompts.

    Contains the fully assembled prompt ready for submission to the LLM,
    along with metadata about the template used and the recommended model.
    """

    prompt: str = Field(..., description="The assembled prompt ready for the LLM", min_length=1)
    template_id: str = Field(
        ..., description="The template used to assemble this prompt", min_length=1
    )
    model: str = Field(
        ...,
        description="Recommended model for this prompt (e.g., mistral-small, mistral-large, meta-llama-33)",
        min_length=1,
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the prompt assembly process",
    )
