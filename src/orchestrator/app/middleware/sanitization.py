import json
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from shared.config.loader import load_orchestrator_config
from shared.config.schemas import OrchestratorConfig
from shared.logging_utils.fastapi import configure_logging

from ..utils.sanitization import sanitize_input
from ..utils.secure_logging import REDACT_LOGS, REDACTION_LEVEL, redact_request_body

logger = configure_logging(
    service_name="sanitization_middleware", log_level="INFO", log_format="json"
)


async def sanitize_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware to sanitize incoming request data for security.

    This function intercepts incoming HTTP requests, extracts the request body,
    and passes it through the LLM-Guard sanitization service if enabled. It logs the
    sanitization results including risk scores and any modifications made.

    Args:
        request (Request): The incoming HTTP request
        call_next (callable): The next middleware or endpoint handler

    Returns:
        Response: The response from the next middleware or endpoint
    """
    settings = _get_settings(request)

    # Check if LLM-Guard sanitization is enabled
    llm_guard_enabled = settings.llm_guard_enabled

    if not llm_guard_enabled:
        logger.debug(
            "LLM-Guard sanitization disabled, skipping request sanitization",
            extra={"path": str(request.url.path), "method": request.method},
        )
        return await call_next(request)
    # Only process body for relevant methods and if body exists
    # NOTE: We intentionally skip sanitization for file uploads (multipart/form-data) to avoid misusing LLM-Guard on large/binary data.
    # LLM-Guard should only be used for user prompts and not for document uploads intended for vector-db storage.
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "").lower()
        if content_type.startswith("multipart/form-data"):
            logger.info(
                "Skipping sanitization for multipart/form-data (file upload) request.",
                extra={"path": str(request.url.path), "method": request.method},
            )
        else:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_text = body_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        body_text = body_bytes.decode("latin-1")
                        logger.warning(
                            "Request body was not UTF-8, decoded as latin-1.",
                            extra={
                                "path": str(request.url.path),
                                "method": request.method,
                            },
                        )
                    except UnicodeDecodeError:
                        logger.error(
                            "Failed to decode request body with UTF-8 or latin-1.",
                            extra={
                                "path": str(request.url.path),
                                "method": request.method,
                            },
                        )
                        # Option: raise an HTTP error, or proceed without sanitizing body,
                        # or use a placeholder. For now, proceed with empty body_text.
                        body_text = ""

                if body_text:  # Proceed with sanitization only if body_text is not empty
                    sanitized_body, risk_score, modified = await sanitize_input(body_text)

                    # Redact sensitive data in logs based on REDACT_LOGS env var
                    if REDACT_LOGS:
                        try:
                            body_json = json.loads(body_text)
                            redacted_body = redact_request_body(body_json)
                            log_original = json.dumps(redacted_body)
                            log_sanitized = log_original if not modified else "[MODIFIED]"
                        except (json.JSONDecodeError, ValueError):
                            # Non-JSON body, redact entire string
                            log_original = f"[REDACTED:{len(body_text)}chars]"
                            log_sanitized = log_original
                    else:
                        # No redaction - log full content
                        log_original = (
                            (body_text[:200] + "...[truncated]")
                            if len(body_text) > 200
                            else body_text
                        )
                        log_sanitized = (
                            (sanitized_body[:200] + "...[truncated]")
                            if len(sanitized_body) > 200
                            else sanitized_body
                        )

                    logger.info(
                        "Request sanitization",
                        extra={
                            "original": log_original,
                            "sanitized": log_sanitized,
                            "risk_score": risk_score,
                            "modified": modified,
                            "path": str(request.url.path),
                            "method": request.method,
                            "redaction_enabled": REDACT_LOGS,
                            "redaction_level": (REDACTION_LEVEL if REDACT_LOGS else "none"),
                        },
                    )
                else:
                    # Log that body was empty or undecodable, so no sanitization applied to body
                    logger.info(
                        "Request body empty or undecodable, no body sanitization applied.",
                        extra={"path": str(request.url.path), "method": request.method},
                    )
            else:
                # Log that body was empty
                logger.info(
                    "Request body is empty, no body sanitization applied.",
                    extra={"path": str(request.url.path), "method": request.method},
                )
    else:
        # For GET, DELETE, etc., log that no body sanitization is applied
        logger.debug(
            f"No body sanitization for {request.method} request.",
            extra={"path": str(request.url.path), "method": request.method},
        )

    return await call_next(request)


def _get_settings(request: Request) -> OrchestratorConfig:
    """Retrieve orchestrator configuration from app state or shared loader."""
    config = getattr(request.app.state, "orchestrator_config", None)
    if config is None:
        config = load_orchestrator_config()
        request.app.state.orchestrator_config = config
    return config
