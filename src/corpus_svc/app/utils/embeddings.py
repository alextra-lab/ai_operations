"""
embeddings.py

Utility functions and dependency providers related to the Embedding Service client.

This module provides a global instance of the EmbeddingServiceClient and a
FastAPI dependency provider to access it. The client is intended to be
initialized at application startup.
"""

from shared.logging_utils.fastapi import configure_logging

from ..clients import (
    EmbeddingServiceClient,  # Ensure this import path is correct based on project structure
)

logging = configure_logging(service_name="embedding_utils")

# Global variable for the EmbeddingServiceClient instance.
# This client is used to interact with the embedding service for generating embeddings.
# It is initialized during the application startup sequence in `main.py`.
embedding_client: EmbeddingServiceClient | None = None


async def get_embedding_client() -> EmbeddingServiceClient | None:
    """
    FastAPI dependency provider for the EmbeddingServiceClient.

    This function returns the globally initialized `embedding_client`.
    It's designed to be used as a dependency in FastAPI path operations
    to ensure that the client is available and properly initialized.

    If the `embedding_client` is None (which should ideally not happen if
    the EMBEDDING_SERVICE_URL is configured and startup is successful),
    a warning is logged. Callers should handle the Optional return type
    appropriately, though in a correctly configured and started application,
    this should always return a valid client instance.

    Returns:
        Optional[EmbeddingServiceClient]: The initialized embedding service client,
                                          or None if it hasn't been initialized.
    """
    if embedding_client is None:
        # This warning indicates a potential issue with the application startup sequence
        # or configuration, as the client should be initialized before any requests
        # requiring it are processed.
        logging.warning(
            "Attempted to get EmbeddingServiceClient, but it's not initialized. "
            "This might indicate an issue with the embedding service URL configuration or "
            "the application startup lifecycle."
        )
    return embedding_client
