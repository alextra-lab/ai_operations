"""
OpenAI-compatible chat completion request models.

Follows OpenAI API specification:
https://platform.openai.com/docs/api-reference/chat/create
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """
    Individual message in a chat conversation.

    OpenAI message format with role and content.
    """

    role: Literal["system", "user", "assistant", "function", "tool"] = Field(
        description="The role of the message author"
    )
    content: str | None = Field(
        default=None,
        description="The content of the message",
    )
    name: str | None = Field(
        default=None,
        description="Optional name for the message author",
    )
    function_call: dict[str, Any] | None = Field(
        default=None,
        description="Optional function call (deprecated, use tool_calls)",
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional tool calls made by the assistant",
    )


class ChatCompletionRequest(BaseModel):
    """
    OpenAI-compatible chat completion request.

    Supports all standard OpenAI parameters for maximum compatibility.
    """

    model: str = Field(description="Model ID (e.g., 'gpt-4o-mini', 'mistral-small')")
    messages: list[ChatMessage] = Field(
        description="List of messages in the conversation",
        min_length=1,
    )

    # Sampling parameters
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability (0.0-1.0)",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate",
    )
    n: int | None = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of completions to generate",
    )

    # Response format
    stream: bool = Field(
        default=False,
        description="Enable SSE streaming response",
    )
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="Response format (e.g., {'type': 'json_object'})",
    )

    # Stop sequences
    stop: str | list[str] | None = Field(
        default=None,
        description="Stop sequence(s) to end generation",
    )

    # Advanced parameters
    presence_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty (-2.0 to 2.0)",
    )
    frequency_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty (-2.0 to 2.0)",
    )
    logit_bias: dict[str, float] | None = Field(
        default=None,
        description="Token logit biases",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for deterministic sampling",
    )

    # User identification
    user: str | None = Field(
        default=None,
        description="Unique user identifier for abuse monitoring",
    )

    # Tools and functions
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tools available to the model",
    )
    tool_choice: str | dict[str, Any] | None = Field(
        default=None,
        description="Tool choice strategy",
    )
    functions: list[dict[str, Any]] | None = Field(
        default=None,
        description="Deprecated: use tools instead",
    )
    function_call: str | dict[str, Any] | None = Field(
        default=None,
        description="Deprecated: use tool_choice instead",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                ],
                "temperature": 0.7,
                "max_tokens": 150,
            }
        }
    )
