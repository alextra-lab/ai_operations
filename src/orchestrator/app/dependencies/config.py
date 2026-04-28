"""
Dependencies for accessing orchestrator configuration.
"""

from fastapi import Request

from shared.config.loader import load_orchestrator_config
from shared.config.schemas import OrchestratorConfig


def get_orchestrator_settings(request: Request) -> OrchestratorConfig:
    """
    Retrieve the orchestrator configuration, caching it on the FastAPI app state.
    """
    config = getattr(request.app.state, "orchestrator_config", None)
    if config is None:
        config = load_orchestrator_config()
        request.app.state.orchestrator_config = config
    return config
