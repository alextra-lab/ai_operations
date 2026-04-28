"""
Response request models for OpenAI-compatible Responses API.

Implements /v1/responses endpoint for stateful conversations.
New OpenAI API (2025) for agentic workflows.

KEY DIFFERENCES FROM /v1/chat/completions:
- Uses 'input' parameter (string or array) instead of 'messages'
- Uses 'instructions' parameter instead of system messages
- Uses 'max_output_tokens' instead of 'max_tokens'
- Supports 'previous_response_id' for server-side state management
- Uses 'store' parameter to persist responses
"""

from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ResponseInputItem(BaseModel):
    """
    Item in responses API input array.

    Can be a message-like object with role and content.
    """

    role: str = Field(..., description="Role: 'user', 'developer', or 'assistant'")

    content: str | list[dict[str, Any]] = Field(
        ..., description="Content (text or multimodal array)"
    )


class ResponseRequest(BaseModel):
    """
    OpenAI-compatible Responses API request.

    This is DIFFERENT from ChatCompletionRequest!
    Uses 'input' and 'instructions' instead of 'messages' array.

    Attributes:
        model: Model ID
        input: User input (string or array) - required if no previous_response_id
        instructions: System instructions (optional, separate from input)
        previous_response_id: ID to continue conversation
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        max_output_tokens: Maximum tokens to generate
        stream: Enable streaming
        store: Store response for later retrieval (default: true)
        tools: Available tools
        metadata: Custom metadata
    """

    model: str = Field(
        ..., description="Model ID", examples=["gpt-5", "mistralai/mistral-small-3.2"]
    )

    input: Optional[Union[str, list[Union[str, ResponseInputItem]]]] = Field(
        default=None, description="User input (string or array of items)"
    )

    instructions: Optional[str] = Field(
        default=None, description="System-level instructions (separate from input)"
    )

    previous_response_id: Optional[str] = Field(
        default=None, description="ID of previous response to continue conversation"
    )

    temperature: Optional[float] = Field(
        default=None, description="Sampling temperature (0.0-2.0)", ge=0.0, le=2.0
    )

    top_p: Optional[float] = Field(
        default=None, description="Nucleus sampling parameter", ge=0.0, le=1.0
    )

    max_output_tokens: Optional[int] = Field(
        default=None, description="Maximum tokens to generate", gt=0
    )

    stream: bool = Field(default=False, description="Enable streaming response")

    store: bool = Field(default=True, description="Store response server-side for retrieval")

    tools: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Tools available for model to call"
    )

    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Custom metadata for tracking"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "model": "gpt-5",
                "input": "What is a cybersecurity threat?",
                "instructions": "You are a cybersecurity expert.",
                "temperature": 0.7,
                "max_output_tokens": 500,
                "store": True,
            }
        }
