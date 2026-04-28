"""
Response response models for OpenAI-compatible Responses API.

Follows OpenAI API response format for stateful conversations.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseContent(BaseModel):
    """
    Content in a response message.

    Can be text or structured content.
    """

    type: str = Field(..., description="Content type (e.g., 'text', 'image_url', 'tool_call')")

    text: Optional[str] = Field(default=None, description="Text content (if type='text')")

    # Additional fields for other content types
    image_url: Optional[dict[str, Any]] = Field(
        default=None, description="Image URL object (if type='image_url')"
    )

    tool_call: Optional[dict[str, Any]] = Field(
        default=None, description="Tool call object (if type='tool_call')"
    )


class ResponseMessage(BaseModel):
    """
    Message in a response.
    """

    role: str = Field(..., description="Message role (typically 'assistant')")

    content: list[ResponseContent] | str = Field(
        ..., description="Message content (array of content objects or string)"
    )


class ResponseUsage(BaseModel):
    """
    Token usage information.
    """

    input_tokens: int = Field(..., description="Number of input tokens", ge=0)

    output_tokens: int = Field(..., description="Number of output tokens", ge=0)

    total_tokens: Optional[int] = Field(
        default=None, description="Total tokens (input + output)", ge=0
    )


class Response(BaseModel):
    """
    OpenAI-compatible responses API response.

    Stateful conversation response with automatic state tracking.

    Attributes:
        id: Response ID (can be used as previous_response_id)
        object: Always "response"
        model: Model ID used
        created: Unix timestamp
        role: Message role (typically "assistant")
        content: Response content
        stop_reason: Why generation stopped
        usage: Token usage information
        metadata: Custom metadata
    """

    id: str = Field(..., description="Response ID (use as previous_response_id to continue)")

    object: str = Field(default="response", description="Object type")

    model: str = Field(..., description="Model ID used")

    created: int = Field(..., description="Unix timestamp", ge=0)

    role: str = Field(..., description="Message role (typically 'assistant')")

    content: list[ResponseContent] = Field(..., description="Response content")

    stop_reason: Optional[str] = Field(
        default=None,
        description="Why generation stopped (e.g., 'stop', 'length', 'tool_calls')",
    )

    usage: ResponseUsage = Field(..., description="Token usage information")

    metadata: Optional[dict[str, Any]] = Field(default=None, description="Custom metadata")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "resp_abc123",
                "object": "response",
                "model": "mistral-nemo-2407",
                "created": 1699000000,
                "role": "assistant",
                "content": [{"type": "text", "text": "This appears to be a phishing attempt..."}],
                "stop_reason": "stop",
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 80,
                    "total_tokens": 200,
                },
            }
        }
