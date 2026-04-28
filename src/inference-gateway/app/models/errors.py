"""
Error response models - OpenAI-compatible error format.

Follows ADR-054 OpenAI Compatibility and Error Taxonomy.

OpenAI Error Structure:
{
    "error": {
        "message": "Human-readable error message",
        "type": "error_type",
        "code": "error_code",
        "param": "parameter_name"  # Optional
    }
}

References:
- https://platform.openai.com/docs/guides/error-codes
- ADR-045: Secure Logging (no secrets in errors)
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    OpenAI-compatible error detail.

    Fields:
        message: Human-readable error description
        type: Error classification (invalid_request_error, rate_limit_error, etc.)
        code: Machine-readable error code
        param: Parameter that caused the error (optional)
    """

    message: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Error type classification")
    code: str = Field(..., description="Machine-readable error code")
    param: str | None = Field(None, description="Parameter that caused error")


class ErrorResponse(BaseModel):
    """
    OpenAI-compatible error response wrapper.

    Structure matches OpenAI API error responses:
    {
        "error": {
            "message": "...",
            "type": "...",
            "code": "..."
        }
    }
    """

    error: ErrorDetail = Field(..., description="Error details")

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_type: str | None = None,
        error_code: str | None = None,
        param: str | None = None,
    ) -> "ErrorResponse":
        """
        Build ErrorResponse from exception.

        Args:
            exception: Exception to convert
            error_type: Override error type (default: gateway_error)
            error_code: Override error code (default: internal_error)
            param: Parameter that caused error (optional)

        Returns:
            ErrorResponse with OpenAI-compatible structure
        """
        # Extract message from exception
        message = str(exception)
        if hasattr(exception, "message"):
            message = exception.message  # type: ignore[attr-defined]

        # Extract error_type from GatewayError subclasses
        if hasattr(exception, "error_type") and not error_type:
            error_type = exception.error_type  # type: ignore[attr-defined]

        if error_type is None:
            error_type = "gateway_error"

        # Default error code
        if error_code is None:
            error_code = "internal_error"

        return cls(
            error=ErrorDetail(
                message=message,
                type=error_type,
                code=error_code,
                param=param,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dict for JSON response.

        Returns:
            Dict with error structure
        """
        return dict(self.model_dump(mode="json", exclude_none=True))


def build_error_response(
    message: str,
    error_type: str = "gateway_error",
    error_code: str = "internal_error",
    param: str | None = None,
) -> ErrorResponse:
    """
    Build error response with OpenAI-compatible structure.

    Args:
        message: Human-readable error message
        error_type: Error classification
        error_code: Machine-readable code
        param: Parameter that caused error (optional)

    Returns:
        ErrorResponse ready for JSON serialization

    Examples:
        >>> err = build_error_response(
        ...     "Model 'gpt-4' not found",
        ...     error_type="invalid_request_error",
        ...     error_code="model_not_found",
        ...     param="model"
        ... )
        >>> err.to_dict()
        {
            "error": {
                "message": "Model 'gpt-4' not found",
                "type": "invalid_request_error",
                "code": "model_not_found",
                "param": "model"
            }
        }
    """
    return ErrorResponse(
        error=ErrorDetail(
            message=message,
            type=error_type,
            code=error_code,
            param=param,
        )
    )
