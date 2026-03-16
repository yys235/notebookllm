"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import ai_search, auth, blocks, health, notes, settings, shares, upload, users

api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(notes.router, prefix="/notes", tags=["Notes"])
api_router.include_router(blocks.router, tags=["Blocks"])
api_router.include_router(shares.router, prefix="/shares", tags=["Share Links"])
api_router.include_router(ai_search.router, prefix="/ai", tags=["AI Search"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])

# Health check endpoints (no prefix, accessed as /api/v1/health, etc.)
api_router.include_router(health.router, tags=["Health"])

__all__ = ["api_router"]
