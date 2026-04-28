"""
Common types and enums shared across modules.
Breaks Circular dependancy.
"""

from enum import Enum


class ProviderType(str, Enum):
    """Types of embedding providers supported by the service."""

    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"
    LOCAL_MODEL = "LOCAL_MODEL"
