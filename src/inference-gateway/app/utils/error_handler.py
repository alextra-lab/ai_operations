"""
Error handler utilities for OpenAI-compatible error responses.

Provides centralized error mapping and response building.
Follows ADR-054 (OpenAI Compatibility and Error Taxonomy).
"""

from fastapi import status
from fastapi.responses import JSONResponse

from ..models.errors import ErrorResponse, build_error_response
from ..utils.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderDisabledError,
    ProviderHTTPError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


def map_exception_to_error_response(exception: Exception) -> tuple[ErrorResponse, int]:
    """
    Map exception to OpenAI-compatible error response and HTTP status.

    Args:
        exception: Exception to map

    Returns:
        Tuple of (ErrorResponse, status_code)

    Examples:
        >>> err, status = map_exception_to_error_response(
        ...     ModelNotFoundError("gpt-4")
        ... )
        >>> err.to_dict()
        {
            "error": {
                "message": "Model 'gpt-4' not found in registry",
                "type": "invalid_request_error",
                "code": "model_not_found"
            }
        }
        >>> status
        404
    """
    # Model not found
    if isinstance(exception, ModelNotFoundError):
        return (
            build_error_response(
                message=exception.message,
                error_type="invalid_request_error",
                error_code="model_not_found",
            ),
            status.HTTP_404_NOT_FOUND,
        )

    # Provider errors (not found or disabled)
    if isinstance(exception, (ProviderNotFoundError, ProviderDisabledError)):
        return (
            build_error_response(
                message=exception.message,
                error_type="provider_error",
                error_code="provider_unavailable",
            ),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Provider timeout
    if isinstance(exception, ProviderTimeoutError):
        return (
            build_error_response(
                message=exception.message,
                error_type="timeout_error",
                error_code="provider_timeout",
            ),
            status.HTTP_504_GATEWAY_TIMEOUT,
        )

    # Rate limit exceeded
    if isinstance(exception, ProviderRateLimitError):
        return (
            build_error_response(
                message=exception.message,
                error_type="rate_limit_error",
                error_code="rate_limit_exceeded",
            ),
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Provider HTTP error
    if isinstance(exception, ProviderHTTPError):
        return (
            build_error_response(
                message=exception.message,
                error_type="provider_http_error",
                error_code=f"http_{exception.status_code}",
            ),
            status.HTTP_502_BAD_GATEWAY,
        )

    # Generic gateway error
    if isinstance(exception, GatewayError):
        return (
            build_error_response(
                message="Internal server error",  # Don't leak details
                error_type="gateway_error",
                error_code="internal_error",
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Unknown exception
    return (
        build_error_response(
            message="Internal server error",
            error_type="unexpected_error",
            error_code="internal_error",
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def create_error_json_response(
    exception: Exception,
    request_id: str | None = None,
) -> JSONResponse:
    """
    Create JSONResponse from exception with OpenAI-compatible error format.

    Args:
        exception: Exception to convert
        request_id: Optional request ID to include in headers

    Returns:
        JSONResponse with error details and appropriate status code

    Examples:
        >>> resp = create_error_json_response(
        ...     ModelNotFoundError("gpt-4"),
        ...     request_id="req_123"
        ... )
        >>> resp.status_code
        404
        >>> resp.headers["X-Request-ID"]
        'req_123'
    """
    error_response, status_code = map_exception_to_error_response(exception)

    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=error_response.to_dict(),
        headers=headers,
    )


def create_error_stream_chunk(exception: Exception) -> str:
    """
    Create SSE-formatted error chunk for streaming responses.

    Args:
        exception: Exception to convert

    Returns:
        SSE chunk string: "data: {json}\\n\\n"

    Examples:
        >>> chunk = create_error_stream_chunk(
        ...     ModelNotFoundError("gpt-4")
        ... )
        >>> chunk
        'data: {"error": {"message": "...", "type": "...", "code": "..."}}\\n\\n'
    """
    error_response, _ = map_exception_to_error_response(exception)
    return f"data: {error_response.model_dump_json()}\n\n"
