"""
FastAPI application for the LLM-Guard service.

This module configures the FastAPI application, sets up CORS and logging,
and defines endpoints for health checks and text validation using the LLMGuard.
"""

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shared.config.loader import load_llm_guard_config
from shared.logging_utils.fastapi import (
    RequestIDLoggerMiddleware,
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    is_verbose_logging_enabled,
)

from .guard import LLMGuard, initialize_models

# Load centralized configuration
llm_guard_config = load_llm_guard_config()
initialize_models(llm_guard_config.models_path)

# Configure logging using centralized config
configure_logging(service_name=llm_guard_config.name)
logger = get_logger(name=llm_guard_config.name)
verbose_logging = is_verbose_logging_enabled()

# Check if service is enabled via centralized config
LLM_GUARD_SERVICE_ENABLED = llm_guard_config.enabled

if not LLM_GUARD_SERVICE_ENABLED:
    logger.warning("LLM Guard Service is disabled via configuration.")

# Create the FastAPI application using centralized config
app = FastAPI(
    title="LLM-Guard-SVC API",
    description="API for validating and sanitizing LLM inputs",
    version=llm_guard_config.version,
)

# Add request ID logging middleware for proper request tracing
app.add_middleware(RequestIDLoggerMiddleware)
app.add_middleware(
    RequestLoggingMiddleware,
    logger=logger,  # type: ignore[arg-type]
    verbose=verbose_logging,
)

if llm_guard_config.enable_cors:
    allow_origins = (
        llm_guard_config.cors_origins if "*" not in llm_guard_config.cors_origins else ["*"]
    )
    app.add_middleware(  # type: ignore[call-arg,arg-type]
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Dependency to get the LLMGuard instance
def get_llm_guard() -> LLMGuard | None:
    """
    Provides the LLMGuard instance with configuration from centralized config.
    Returns None if the service is disabled.

    Uses the module-level logger instead of injecting it as a dependency to avoid
    FastAPI dependency resolution conflicts.
    """
    if not LLM_GUARD_SERVICE_ENABLED:
        return None

    # Use centralized config for all settings
    fail_fast = llm_guard_config.fail_fast
    cache_enabled = llm_guard_config.cache_enabled
    cache_max_size = llm_guard_config.cache_max_size
    cache_ttl_seconds = llm_guard_config.cache_ttl_seconds

    logger.info(
        "Initializing LLMGuard with config: fail_fast=%s, cache_enabled=%s, "
        "cache_max_size=%s, cache_ttl_seconds=%s",
        fail_fast,
        cache_enabled,
        cache_max_size,
        cache_ttl_seconds,
    )

    return LLMGuard(
        logger=logger,  # type: ignore  # LLMGuard accepts Any for logger
        fail_fast=fail_fast,
        cache_enabled=cache_enabled,
        cache_max_size=cache_max_size,
        cache_ttl_seconds=cache_ttl_seconds,
        regex_engine=llm_guard_config.regex_engine,
        secrets_engine=llm_guard_config.secrets_engine,
    )


class ValidationRequest(BaseModel):
    """
    Request model for input validation.

    Attributes:
        input_text (str): Text input to validate and sanitize.
        context (Optional[Dict[str, str]]): Optional context information for validation.
        strict_mode (bool): If True, apply stricter validation rules.
    """

    input_text: str = Field(..., description="Text input to validate and sanitize")
    context: dict[str, str] | None = Field(
        default=None, description="Optional context for validation"
    )
    strict_mode: bool = Field(False, description="Whether to apply stricter validation rules")


class ValidationResponse(BaseModel):
    """
    Response model for validation results.

    Attributes:
        sanitized_text (str): The sanitized output text.
        risk_score (float): Calculated risk score (0-1, where higher means higher risk).
        modified (bool): Indicates whether the input text was modified during validation.
        details (Dict): Detailed results from the scanning process.
    """

    sanitized_text: str = Field(..., description="Sanitized output text")
    risk_score: float = Field(..., description="Risk score (0-1, higher is riskier)")
    modified: bool = Field(..., description="Whether the input was modified")
    details: dict = Field(..., description="Detailed scanner results")


@app.get("/health")
async def health_check() -> dict[str, str | None]:
    """
    Health check endpoint.

    Returns:
        dict: A JSON object with service status information.
    """
    return {
        "status": "healthy",
        "service": llm_guard_config.name,
        "version": llm_guard_config.version,
    }


@app.post("/api/validate", response_model=ValidationResponse)
async def validate_input(
    request: ValidationRequest,
    req: Request,
    llm_guard_instance: LLMGuard | None = Depends(get_llm_guard),  # ← Re-enabled!
    x_user_id: str | None = Header(None),
    x_request_id: str | None = Header(None),
) -> ValidationResponse:
    """
    Validate and sanitize input text.

    This endpoint processes the input text using the LLMGuard for validation.
    It returns the sanitized text, a risk score, a flag indicating if the input was modified,
    and detailed scanner results. If LLM_GUARD_SERVICE_ENABLED is false, it returns a
    "disabled" status without performing scans.

    Args:
        request (ValidationRequest): The request body containing input text and optional context.
        req (Request): The FastAPI request object.
        llm_guard_instance (Optional[LLMGuard]): The LLMGuard instance, or None if disabled.
        x_user_id (Optional[str]): Optional header containing the user ID.
        x_request_id (Optional[str]): Optional header containing the request ID.

    Returns:
        ValidationResponse: The response model containing validation details.

    Raises:
        HTTPException: If an error occurs during validation processing.
    """
    request_id_for_log = x_request_id or req.headers.get("x-request-id")

    if llm_guard_instance is None:  # Service is disabled
        logger.info(
            "LLM Guard service is disabled. Skipping validation and returning original input.",
            extra={"user_id": x_user_id} if x_user_id else {},
        )
        return ValidationResponse(
            sanitized_text=request.input_text,
            risk_score=0.0,
            modified=False,
            details={
                "status": "disabled",
                "message": "LLM Guard service is currently disabled. No scanning performed.",
            },
        )

    # If llm_guard_instance is not None, proceed with validation
    try:
        # Retrieve validation parameters.
        input_text = request.input_text
        context = request.context

        # Log the validation attempt
        logger.info(
            "Processing validation request for input length: %d",
            len(input_text),
            extra={"user_id": x_user_id} if x_user_id else {},
        )

        # Process input validation via LLMGuard.
        sanitized_text, risk_score, modified, details = llm_guard_instance.validate_input(
            input_text=input_text,
            user_id=x_user_id,
            request_id=request_id_for_log,
            _context=context,
            logger=logger,  # Pass the module-level logger
        )

        # Log the validation result
        logger.info(
            "Validation completed. Risk score: %s, Modified: %s",
            risk_score,
            modified,
            extra={"user_id": x_user_id} if x_user_id else {},
        )

        # Construct the response.
        return ValidationResponse(
            sanitized_text=sanitized_text,
            risk_score=risk_score,
            modified=modified,
            details=details,
        )

    except Exception as e:
        logger.error(
            "Validation error: %s",
            type(e).__name__,
            exc_info=True,
            extra={"user_id": x_user_id} if x_user_id else {},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed",
        ) from e


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions and return a generic error response.

    Args:
        request (Request): The incoming HTTP request.
        exc (Exception): The unhandled exception.

    Returns:
        JSONResponse: A JSON error response with HTTP status 500.
    """
    logger.error(
        "Unhandled exception: %s",
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )
