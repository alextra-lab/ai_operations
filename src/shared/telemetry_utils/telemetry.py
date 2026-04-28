"""
Shared Telemetry Utilities

Provides OpenTelemetry tracing setup and utility functions for FastAPI applications.
Intended for use across all services.

Usage:
    from shared.telemetry_utils.telemetry import setup_telemetry, get_tracer, get_trace_id, ...

    setup_telemetry(
        app,
        service_name="my-service",
        service_version="1.0.0",
        deployment_environment="development",
        otlp_endpoint="http://otel-collector:4317"
    )
"""

from __future__ import annotations

from typing import Any

from shared.logging_utils.fastapi import configure_logging

# Use a logger specific to telemetry utilities
logger = configure_logging(service_name="shared.telemetry_utils")

# Conditional imports for OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


def setup_telemetry(
    app: Any = None,
    service_name: str = "service",
    service_version: str = "1.0.0",
    deployment_environment: str = "development",
    otlp_endpoint: str | None = None,
    instrument_fastapi: bool = True,
) -> None:
    """
    Set up OpenTelemetry for the application.

    Configures trace provider, exporters, and instrumentation if OpenTelemetry is available.
    If not available, logs a warning and continues without telemetry.

    Args:
        app: The FastAPI application instance (optional, only needed if instrument_fastapi is True)
        service_name: Name of the service for resource attribution
        service_version: Version of the service
        deployment_environment: Deployment environment (e.g., "production", "staging")
        otlp_endpoint: OTLP exporter endpoint (e.g., "http://otel-collector:4317")
        instrument_fastapi: Whether to instrument FastAPI automatically

    Returns:
        None
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry packages not available, telemetry will not be enabled")
        return

    # Configure trace context propagation
    TraceContextTextMapPropagator()

    # Configure trace provider with service info
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": deployment_environment,
        }
    )

    provider = TracerProvider(resource=resource)

    # Set up exporter if endpoint is configured
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)
        logger.info("OpenTelemetry OTLP exporter configured")
    else:
        logger.warning("OTLP endpoint not set, traces will not be exported")

    # Set global trace provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI app if requested
    if instrument_fastapi and app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumentation enabled.")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    logger.info("OpenTelemetry initialized for %s", service_name)


def get_tracer(name: str) -> Any:
    """
    Get a tracer for the specified component.

    Args:
        name: Component name

    Returns:
        OpenTelemetry tracer instance or DummyTracer if unavailable
    """
    if not OPENTELEMETRY_AVAILABLE:
        return DummyTracer()
    return trace.get_tracer(name)


def extract_context_from_headers(headers: dict[str, str]) -> Any:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: HTTP headers

    Returns:
        Extracted context or None if OpenTelemetry is not available
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None
    return TraceContextTextMapPropagator().extract(carrier=headers)


def inject_context_into_headers(headers: dict[str, str], context: Any = None) -> dict[str, str]:
    """
    Inject trace context into HTTP headers.

    Args:
        headers: HTTP headers to inject context into
        context: Context to inject (uses current context if None)

    Returns:
        Updated headers
    """
    if not OPENTELEMETRY_AVAILABLE:
        return headers
    context = context or trace.get_current_span().get_span_context()
    TraceContextTextMapPropagator().inject(carrier=headers, context=context)  # type: ignore
    return headers


def get_current_span_context() -> Any:
    """
    Get the current span context.

    Returns:
        Current span context or None if OpenTelemetry is not available
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None
    return trace.get_current_span().get_span_context()


def get_trace_id() -> str | None:
    """
    Get the current trace ID.

    Returns:
        Current trace ID as string or None if not available
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None
    context = trace.get_current_span().get_span_context()
    if context and getattr(context, "trace_id", None):
        return format(context.trace_id, "032x")
    return None


def get_span_id() -> str | None:
    """
    Get the current span ID.

    Returns:
        Current span ID as string or None if not available
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None
    context = trace.get_current_span().get_span_context()
    if context and getattr(context, "span_id", None):
        return format(context.span_id, "016x")
    return None


class DummyTracer:
    """
    Dummy tracer that provides no-op implementations of tracer methods.
    Used when OpenTelemetry is not available.
    """

    def start_as_current_span(
        self, _name: str, _context: Any = None, _kind: Any = None
    ) -> DummySpan:
        return DummySpan()

    def start_span(self, _name: str) -> DummySpan:
        return DummySpan()


class DummySpan:
    """
    Dummy span that provides no-op implementations of span methods.
    Used when OpenTelemetry is not available.
    """

    def __enter__(self) -> DummySpan:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def end(self) -> None:
        pass

    def get_span_context(self) -> None:
        return None


def create_span(name: str, parent_context: Any = None) -> Any:
    """
    Create a new span.

    Args:
        name: Span name
        parent_context: Parent context

    Returns:
        Span context manager
    """
    if not OPENTELEMETRY_AVAILABLE:
        return DummySpan()
    tracer = get_tracer(__name__)
    return tracer.start_as_current_span(name, context=parent_context)


def set_span_attribute(key: str, value: str) -> None:
    """
    Set attribute on current span.

    Args:
        key: Attribute key
        value: Attribute value

    Returns:
        None
    """
    if not OPENTELEMETRY_AVAILABLE:
        return
    current_span = trace.get_current_span()
    if hasattr(current_span, "set_attribute"):
        current_span.set_attribute(key, value)


def record_exception(exception: Exception) -> None:
    """
    Record exception in current span.

    Args:
        exception: Exception to record

    Returns:
        None
    """
    if not OPENTELEMETRY_AVAILABLE:
        return
    current_span = trace.get_current_span()
    if hasattr(current_span, "record_exception"):
        current_span.record_exception(exception)
