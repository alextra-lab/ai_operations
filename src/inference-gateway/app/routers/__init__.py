"""
API routers for Inference Gateway.

All routers follow OpenAI API specification for compatibility.
"""

from .admin import router as admin_router
from .chat import router as chat_router
from .embeddings import router as embeddings_router
from .responses import router as responses_router

__all__ = ["admin_router", "chat_router", "embeddings_router", "responses_router"]
