"""
OpenAI-compatible request and response models.

These models follow OpenAI's chat completions API specification
for maximum compatibility with existing clients.
"""

from .requests import ChatCompletionRequest, ChatMessage
from .responses import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionResponse,
    ChatCompletionUsage,
)

__all__ = [
    "ChatCompletionChoice",
    "ChatCompletionMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionUsage",
    "ChatMessage",
]
