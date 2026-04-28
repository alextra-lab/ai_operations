"""
Gateway-specific exception classes.

Follows ADR-054 OpenAI Compatibility and Error Taxonomy.
"""


class GatewayError(Exception):
    """Base exception for all Gateway errors."""

    def __init__(self, message: str, error_type: str = "gateway_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class ModelNotFoundError(GatewayError):
    """Requested model not found in registry."""

    def __init__(self, model_id: str):
        super().__init__(
            message=f"Model '{model_id}' not found in registry",
            error_type="model_not_found",
        )
        self.model_id = model_id


class ProviderNotFoundError(GatewayError):
    """Provider not found or disabled."""

    def __init__(self, provider_name: str):
        super().__init__(
            message=f"Provider '{provider_name}' not found or disabled",
            error_type="provider_not_found",
        )
        self.provider_name = provider_name


class ProviderDisabledError(GatewayError):
    """Provider is disabled."""

    def __init__(self, provider_name: str):
        super().__init__(
            message=f"Provider '{provider_name}' is disabled",
            error_type="provider_disabled",
        )
        self.provider_name = provider_name


class ProviderTimeoutError(GatewayError):
    """Provider request timed out."""

    def __init__(self, provider_name: str, timeout_seconds: float):
        super().__init__(
            message=f"Provider '{provider_name}' timed out after {timeout_seconds}s",
            error_type="provider_timeout",
        )
        self.provider_name = provider_name
        self.timeout_seconds = timeout_seconds


class ProviderHTTPError(GatewayError):
    """Provider returned HTTP error."""

    def __init__(self, provider_name: str, status_code: int, detail: str = ""):
        super().__init__(
            message=f"Provider '{provider_name}' error {status_code}: {detail}",
            error_type="provider_http_error",
        )
        self.provider_name = provider_name
        self.status_code = status_code
        self.detail = detail


class ProviderRateLimitError(GatewayError):
    """Provider rate limit exceeded."""

    def __init__(self, provider_name: str, retry_after: int | None = None):
        msg = f"Provider '{provider_name}' rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(message=msg, error_type="provider_rate_limit")
        self.provider_name = provider_name
        self.retry_after = retry_after


class InvalidConfigurationError(GatewayError):
    """Invalid provider configuration."""

    def __init__(self, provider_name: str, reason: str):
        super().__init__(
            message=f"Invalid configuration for provider '{provider_name}': {reason}",
            error_type="invalid_configuration",
        )
        self.provider_name = provider_name
        self.reason = reason
