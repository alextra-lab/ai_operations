"""
Security-related utilities and dependencies for the Embedding Service.
"""

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from shared.config.loader import load_embedding_config
from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="security")

API_KEY_NAME = "X-API-Key"
EMBEDDING_SERVICE_CLIENT_API_KEY_ENV = "EMBEDDING_SERVICE_CLIENT_API_KEY"

api_key_header_auth = APIKeyHeader(
    name=API_KEY_NAME, auto_error=True
)  # auto_error=True for strict checking


async def verify_client_api_key(
    api_key_header: str = Security(api_key_header_auth),
) -> bool:
    """
    Verify the X-API-Key for client-to-service authentication.
    This key is used by trusted internal clients (e.g. corpus service, orchestrator).

    Returns:
        bool: True if the API key is valid.

    Raises:
        HTTPException: If the API key is missing or invalid, or if not configured.
    """
    expected_api_key = load_embedding_config().client_api_key

    if not expected_api_key:
        logger.error(
            "Client API key not configured in environment variable '%s'.",
            EMBEDDING_SERVICE_CLIENT_API_KEY_ENV,
            extra={"request_id": "startup"},
        )
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: Client API key not configured.",
        )

    if not api_key_header or api_key_header != expected_api_key:
        logger.warning(
            "Invalid or missing Client API Key.",
            extra={"request_id": "auth-failure"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Client API Key.",
        )

    logger.info(
        "Client API Key authentication succeeded.",
        extra={"request_id": "auth-success"},
    )
    return True
