"""OpenTelemetry distributed tracing configuration.

This module sets up distributed tracing using OpenTelemetry.
Traces are exported to an OTLP collector (e.g., Jaeger, Tempo).
"""
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.core.config import get_settings

settings = get_settings()


def setup_tracing(app: Any | None = None) -> TracerProvider:
    """Configure and initialize OpenTelemetry tracing.

    Args:
        app: Optional FastAPI app instance to instrument

    Returns:
        TracerProvider: Configured tracer provider
    """
    # Define service resource
    resource = Resource.create({
        SERVICE_NAME: settings.OTEL_SERVICE_NAME,
        "service.version": settings.APP_VERSION,
        "deployment.environment": "production" if not settings.DEBUG else "development",
        "service.language": "python",
    })

    # Configure sampling (sample 100% in dev, 10% in prod)
    sampling_ratio = 1.0 if settings.DEBUG else 0.1

    # Create tracer provider
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sampling_ratio),
    )

    # Configure OTLP exporter
    otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

    # Use batch processor for better performance
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI if provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=provider,
            excluded_urls="/health,/health/ready,/health/live,/metrics",
        )

    # Instrument HTTP client (httpx)
    HTTPXClientInstrumentor().instrument()

    # Instrument SQLAlchemy (must be called before engine creation)
    # Note: This is typically called in database.py during engine initialization

    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual instrumentation.

    Args:
        name: Name of the component/module

    Returns:
        Tracer: Configured tracer instance

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation"):
            # do work
    """
    return trace.get_tracer(name)


class AsyncTracer:
    """Helper class for tracing async operations."""

    def __init__(self, name: str):
        """Initialize tracer for a component.

        Args:
            name: Component name for the tracer
        """
        self.tracer = get_tracer(name)

    async def trace_operation(
        self,
        operation_name: str,
        attributes: dict[str, Any] | None = None,
    ):
        """Context manager for tracing async operations.

        Args:
            operation_name: Name of the operation being traced
            attributes: Optional span attributes

        Yields:
            Span: The current span for adding attributes

        Example:
            async with tracer.trace_operation("ai_search", {"query": "test"}):
                result = await search_function()
        """
        span = self.tracer.start_as_current_span(
            operation_name,
            attributes=attributes or {},
        )
        try:
            yield span
        finally:
            span.end()
