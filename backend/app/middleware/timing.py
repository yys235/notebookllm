"""Request timing middleware for performance monitoring with Prometheus metrics."""
import time
from typing import Callable

from prometheus_client import Gauge
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger
from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)

logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Record request processing time for monitoring and Prometheus metrics.

    This middleware:
    - Records request duration to Prometheus histogram
    - Tracks in-flight requests with Prometheus gauge
    - Counts requests by method, path, and status code
    - Adds X-Process-Time header
    - Logs slow requests (>1s)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and record timing metrics.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response: Response with timing headers and metrics recorded
        """
        # Get normalized path for metrics (replace path parameters)
        path = _get_metric_path(request)

        # Track in-flight requests
        http_requests_in_progress.labels(
            method=request.method,
            path=path,
        ).inc()

        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record Prometheus metrics
            http_request_duration_seconds.labels(
                method=request.method,
                path=path,
            ).observe(duration)

            http_requests_total.labels(
                method=request.method,
                path=path,
                status_code=response.status_code,
            ).inc()

            # Add timing header
            response.headers["X-Process-Time"] = f"{duration * 1000:.2f}ms"

            # Log slow requests (>1s)
            duration_ms = duration * 1000
            if duration_ms > 1000:
                correlation_id = getattr(request.state, "correlation_id", "unknown")
                logger.warning(
                    "Slow request detected",
                    correlation_id=correlation_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=f"{duration_ms:.2f}",
                )

            return response

        finally:
            # Decrement in-flight requests
            http_requests_in_progress.labels(
                method=request.method,
                path=path,
            ).dec()


def _get_metric_path(request: Request) -> str:
    """Get normalized path for Prometheus metrics.

    Replaces path parameters with placeholder names to reduce cardinality.

    Examples:
        /api/v1/notes/123 -> /api/v1/notes/{id}
        /api/v1/shares/abc123 -> /api/v1/shares/{token}

    Args:
        request: The incoming request

    Returns:
        Normalized path string
    """
    path = request.url.path

    # Common path parameter patterns
    patterns = [
        # UUID pattern
        (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{uuid}"),
        # Numeric ID
        (r"/\d+(?=/|$)", "/{id}"),
        # Share token pattern (alphanumeric strings)
        (r"/shares/[a-zA-Z0-9_-]+(?=/|$)", "/shares/{token}"),
        # Username pattern
        (r"/users/[^/]+(?=/|$)", "/users/{username}"),
    ]

    for pattern, replacement in patterns:
        path = re.sub(pattern, replacement, path)

    return path


import re
