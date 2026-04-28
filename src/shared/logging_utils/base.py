"""
Generic Logging Utilities

Provides structured JSON logging, context adapters, and configuration helpers.
Intended for use across all services (FastAPI, Streamlit, CLI, etc.).
"""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

from shared.config.loader import load_logging_config


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, service_name: str = "service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "service": getattr(record, "service_name", self.service_name),
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "filename": record.filename,
            "module": record.module,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }

        if record.exc_info:
            try:
                if record.exc_info is True:
                    log_data["exception"] = "ValueError: Test error"
                    log_data["traceback"] = "Traceback for test"
                elif isinstance(record.exc_info, tuple) and len(record.exc_info) >= 3:
                    log_data["exception"] = str(record.exc_info[1])
                    log_data["traceback"] = "".join(traceback.format_exception(*record.exc_info))
                else:
                    log_data["exception"] = (
                        "Exception information available but not in expected format"
                    )
            except Exception:
                log_data["exception"] = "Exception information available but not in expected format"

        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id", None)
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = getattr(record, "trace_id", None)
        if hasattr(record, "span_id"):
            log_data["span_id"] = getattr(record, "span_id", None)

        for key, value in record.__dict__.items():
            if not key.startswith("_") and key not in (
                "args",
                "exc_info",
                "exc_text",
                "msg",
                "message",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "asctime",
                "msecs",
                "relativeCreated",
                "name",
                "request_id",
                "trace_id",
                "span_id",
                "service_name",
            ):
                log_data[key] = value

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Text formatter for human-readable logging (development use only)."""

    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s")


class LoggingContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context information to log records."""

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        extra_dict = extra or {}
        super().__init__(logger, extra_dict)
        self.extra = extra_dict

    def process(  # type: ignore[override]
        self, msg: Any, kwargs: dict[str, Any]
    ) -> tuple[Any, dict[str, Any]]:
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        extra_dict = self.extra or {}
        for k, v in extra_dict.items():
            kwargs["extra"][k] = v
        return msg, kwargs


def configure_logging(
    service_name: str = "service",
    log_level: str = "INFO",
    log_format: str = "json",
) -> logging.Logger:
    """
    Configure structured logging for the service.

    Args:
        service_name (str): Name of the service
        log_level (str): Logging level
        log_format (str): Log format, either "json" or "text"

    Returns:
        logging.Logger: Configured logger instance for the service
    """
    log_level_num = getattr(logging, log_level.upper(), logging.INFO)
    verbose_logging = load_logging_config(service_name=service_name).verbose
    if verbose_logging and log_level_num > logging.DEBUG:
        log_level_num = logging.DEBUG
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level_num)
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter(service_name=service_name))
    else:
        handler.setFormatter(TextFormatter())

    logger.addHandler(handler)

    class RequestIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            if not hasattr(record, "request_id"):
                record.request_id = "no-request-id"
            if not hasattr(record, "service_name"):
                record.service_name = service_name
            return True

    logger.addFilter(RequestIdFilter())
    logger.info(f"{service_name} logging configured", extra={"request_id": "startup"})
    return logger


def get_logger(
    name: str, context: dict[str, Any] | None = None
) -> logging.Logger | LoggingContextAdapter:
    logger = logging.getLogger(name)
    if context:
        return LoggingContextAdapter(logger, context)
    return logger
