"""
Utilities for converting shared orchestrator configuration into runtime dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.config.schemas import OrchestratorConfig


def build_runtime_config(settings: OrchestratorConfig) -> dict[str, object]:
    """
    Convert `OrchestratorConfig` model into the legacy runtime dict expected by
    orchestrator components. This allows gradual migration away from dict-based
    configuration while the rest of the stack is refactored.
    """
    return {
        "llm_guard_enabled": settings.llm_guard_enabled,
        "llm_guard_url": settings.llm_guard_service_url,
        "llm_guard_timeout": settings.llm_guard_timeout_seconds,
        "inference_gateway_url": settings.inference_gateway_url,
        "retrieval_svc_url": settings.retrieval_service_url,
        "retrieval_enabled": settings.retrieval_enabled,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "dashboard_health_endpoints": settings.dashboard_health_endpoints,
        "tool_secrets_key": settings.tool_secrets_key,
        "pricing_default_input_per_million": settings.pricing_default_input_per_million,
        "pricing_default_output_per_million": settings.pricing_default_output_per_million,
    }
