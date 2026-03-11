"""Health check endpoints with dependency status."""
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity and latency."""
    start_time = datetime.now(UTC)
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity and latency."""
    start_time = datetime.now(UTC)
    try:
        from app.core.redis import get_redis_client
        r = await get_redis_client()
        await r.ping()
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_ai_service() -> dict[str, Any]:
    """Check AI service connectivity (optional for service operation)."""
    if not settings.AI_SERVICE_URL and not settings.AI_API_KEY:
        return {"status": "disabled", "message": "AI service not configured"}

    start_time = datetime.now(UTC)
    try:
        import httpx
        if settings.AI_API_KEY:
            # Test OpenAI API connectivity
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}
                )
                if response.status_code == 200:
                    latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
        return {"status": "unhealthy", "error": "AI service unreachable"}
    except Exception as e:
        logger.warning("AI service health check failed", error=str(e))
        return {"status": "degraded", "error": str(e)}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint for load balancers and monitoring.

    Returns minimal status information suitable for frequent polling.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Readiness probe with comprehensive dependency checks.

    Use this endpoint to determine if the service is ready to receive traffic.
    Returns status of all critical dependencies (database, redis, ai_service).
    """
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(),
        "ai_service": await check_ai_service(),
    }

    # Determine overall readiness
    # Service is ready if database and redis are healthy (ai_service can be disabled/degraded)
    critical_healthy = all(
        checks.get("database", {}).get("status") == "healthy" and
        checks.get("redis", {}).get("status") == "healthy"
    )

    overall_status = "ready" if critical_healthy else "not_ready"

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe - indicates if the service is running.

    If this endpoint returns 200, Kubernetes/infrastructure will consider
    the service alive. If it fails, the service may be restarted.
    """
    return {"status": "alive"}
