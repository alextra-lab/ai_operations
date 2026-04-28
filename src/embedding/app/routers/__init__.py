"""
API route handlers for the embedding service.
"""

from .admin import router as admin_router
from .embedding import router as embedding_router

__all__ = [
    "admin_router",
    "embedding_router",
]
