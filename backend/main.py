"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logger import configure_logging, get_logger
from app.core.redis import close_redis
from app.middleware import CorrelationIdMiddleware, ErrorHandlerMiddleware, TimingMiddleware

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Manages application startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("Starting application", version=settings.APP_VERSION, environment=settings.ENVIRONMENT)

    # Validate security configuration
    try:
        settings.validate_security_config()
        logger.info("Security configuration validated")
    except ValueError as e:
        logger.error("Security validation failed", error=str(e))
        raise RuntimeError(f"Security validation failed: {e}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close connections
    await close_db()
    await close_redis()

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (order matters)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(TimingMiddleware)

    # Include API routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Mount static files for uploaded images
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {"status": "healthy", "version": settings.APP_VERSION}

    # Metrics endpoint (Prometheus)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
        }

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
