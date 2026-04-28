"""
Shared provider models and types.

Consolidates provider configuration schemas used across services:
- Inference Gateway
- Backend Orchestrator
- Embedding Service

Prevents schema drift and ensures consistent validation.
"""

from .models import (
    ConnectionConfig,
    ModelConfig,
    ProviderConfig,
    ProviderConfigUpdate,
    ProviderListResponse,
    ProviderStatus,
    ProviderTestResult,
    ProviderType,
)

__all__ = [
    "ConnectionConfig",
    "ModelConfig",
    "ProviderConfig",
    "ProviderConfigUpdate",
    "ProviderListResponse",
    "ProviderStatus",
    "ProviderTestResult",
    "ProviderType",
]
