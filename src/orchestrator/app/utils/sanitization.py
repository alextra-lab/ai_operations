import httpx

from shared.config.loader import load_orchestrator_config
from shared.logging_utils.fastapi import configure_logging

# Configure logger for this module
logger = configure_logging(service_name="utils_sanitization")

# LLM Guard service URL (from environment or default to container name)
LLM_GUARD_URL = load_orchestrator_config().llm_guard_service_url


async def sanitize_input(
    input_text: str,
    user_id: str | None = None,
    request_id: str | None = None,
    context: dict[str, str] | None = None,
) -> tuple[str, float, bool]:
    """
    Sanitize input by calling the LLM-Guard-SVC.

    Args:
        input_text: Text to sanitize
        user_id: Optional user ID for audit logging
        request_id: Optional request ID for tracing
        context: Optional context for validation

    Returns:
        Tuple containing:
        - Sanitized text (or original if validation passes)
        - Risk score (0-1, higher is riskier)
        - Flag indicating if the text was modified

    Raises:
        Exception: If validation fails or service is unavailable
    """
    try:
        # Prepare headers for request
        headers = {}
        if user_id:
            headers["x-user-id"] = user_id
        if request_id:
            headers["x-request-id"] = request_id

        # Prepare request payload
        payload = {
            "input_text": input_text,
            "context": context or {},
            "strict_mode": False,  # Can be configurable based on requirements
        }

        # Call LLM-Guard service
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{LLM_GUARD_URL}/api/validate", json=payload, headers=headers
            )

        # Check for successful response
        if response.status_code != 200:
            logger.error(
                f"LLM-Guard validation failed with status {response.status_code}: {response.text}"
            )
            # Fall back to returning original input on error
            return input_text, 0.0, False

        # Parse response
        result = response.json()
        sanitized_text = result.get("sanitized_text", input_text)
        risk_score = result.get("risk_score", 0.0)
        modified = result.get("modified", False)

        # Log the validation results
        if modified or risk_score > 0.5:
            logger.warning(
                f"Input sanitized - Risk score: {risk_score}, Modified: {modified}",
                extra={
                    "risk_score": risk_score,
                    "modified": modified,
                    "user_id": user_id,
                    "request_id": request_id,
                },
            )
        else:
            logger.info(
                f"Input validated - Risk score: {risk_score}, Modified: {modified}",
                extra={
                    "risk_score": risk_score,
                    "modified": modified,
                    "user_id": user_id,
                    "request_id": request_id,
                },
            )

        return sanitized_text, risk_score, modified

    except Exception as e:
        logger.exception(f"Error calling LLM-Guard service: {e!s}")
        # Fall back to returning original input on error
        return input_text, 0.0, False
