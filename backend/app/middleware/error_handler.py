"""Global error handling middleware."""
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.logger import get_logger

logger = get_logger(__name__)


class ErrorResponse:
    """Standardized error response structure."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize error response.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.code = code or "INTERNAL_ERROR"
        self.details = details

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            dict: Error response as dictionary
        """
        result = {"message": self.message, "code": self.code}
        if self.details:
            result["details"] = self.details
        return result


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler for unhandled exceptions."""

    async def dispatch(self, request: Request, call_next):
        """Process request and handle exceptions.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response: Response or error response
        """
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            correlation_id = getattr(request.state, "correlation_id", "unknown")
            log_context = {"correlation_id": correlation_id, "path": request.url.path}

            # Handle specific HTTP exceptions
            if hasattr(exc, "status_code"):
                status_code = exc.status_code
                message = getattr(exc, "detail", str(exc))
                code = getattr(exc, "code", None)

                logger.warning("HTTP error", **log_context, status=status_code, message=message)
                return JSONResponse(
                    status_code=status_code,
                    content=ErrorResponse(message=message, code=code).to_dict(),
                )

            # Handle validation errors
            if "validation" in str(exc).lower():
                logger.warning("Validation error", **log_context, error=str(exc))
                return JSONResponse(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    content=ErrorResponse(
                        message="Validation failed",
                        code="VALIDATION_ERROR",
                        details={"error": str(exc)},
                    ).to_dict(),
                )

            # Handle authentication errors
            if "authentication" in str(exc).lower() or "unauthorized" in str(exc).lower():
                logger.warning("Authentication error", **log_context, error=str(exc))
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content=ErrorResponse(
                        message="Authentication required",
                        code="AUTHENTICATION_ERROR",
                    ).to_dict(),
                )

            # Handle authorization errors
            if "permission" in str(exc).lower() or "forbidden" in str(exc).lower():
                logger.warning("Authorization error", **log_context, error=str(exc))
                return JSONResponse(
                    status_code=HTTP_403_FORBIDDEN,
                    content=ErrorResponse(
                        message="Insufficient permissions",
                        code="AUTHORIZATION_ERROR",
                    ).to_dict(),
                )

            # Handle not found errors
            if "not found" in str(exc).lower():
                logger.warning("Not found error", **log_context, error=str(exc))
                return JSONResponse(
                    status_code=HTTP_404_NOT_FOUND,
                    content=ErrorResponse(
                        message="Resource not found",
                        code="NOT_FOUND",
                    ).to_dict(),
                )

            # Log and handle unexpected errors
            logger.error("Unhandled exception", **log_context, error=str(exc), exc_info=True)
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    message="Internal server error",
                    code="INTERNAL_ERROR",
                ).to_dict(),
            )
