"""AI Search and RAG routes."""
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.dependencies import CurrentUser
from app.schemas.ai_search import (
    AIAnswerRequest,
    AIAnswerResponse,
    AISummaryResponse,
    IndexNotesRequest,
    IndexNoteRequest,
    IndexResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.ai_search import AISearchService

router = APIRouter()
logger = get_logger(__name__)

# Type aliases
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    data: SemanticSearchRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Perform semantic search using AI embeddings.

    Finds notes similar to the query using vector similarity.
    """
    service = AISearchService(db)

    start_time = time.time()
    results = await service.semantic_search(
        query=data.query,
        user_id=current_user.id,
        limit=data.limit,
    )
    duration_ms = int((time.time() - start_time) * 1000)

    # Record search history
    await service.record_search(
        user_id=current_user.id,
        query=data.query,
        search_type="semantic",
        results_count=len(results),
        duration_ms=duration_ms,
    )

    # Convert to response format
    search_results = [
        SemanticSearchResult(
            note_id=r.note_id,
            chunk_id=r.chunk_id,
            title=r.title,
            content=r.content,
            score=r.score,
            highlights=r.highlights,
        )
        for r in results
    ]

    return SemanticSearchResponse(
        query=data.query,
        results=search_results,
        total=len(search_results),
    )


@router.post("/notes/{note_id}/summarize", response_model=AISummaryResponse)
async def summarize_note(
    note_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Generate AI summary for a note.

    Creates a concise summary and extracts key points.
    """
    service = AISearchService(db)

    summary = await service.summarize_note(
        note_id=note_id,
        user_id=current_user.id,
    )

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not available",
        )

    return AISummaryResponse(
        summary=summary.summary,
        key_points=summary.key_points,
        model=summary.model,
    )


@router.post("/qa", response_model=AIAnswerResponse)
async def ask_question(
    data: AIAnswerRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Ask a question and get an AI answer using RAG.

    The AI searches through your notes to find relevant information
    and provides a comprehensive answer with sources.
    """
    service = AISearchService(db)

    answer = await service.answer_question(
        question=data.question,
        user_id=current_user.id,
        note_ids=data.note_ids,
    )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not available",
        )

    return AIAnswerResponse(
        answer=answer.answer,
        sources=answer.sources,
        model=answer.model,
        confidence=answer.confidence,
    )


@router.post("/notes/index", response_model=IndexResponse)
async def index_note(
    data: IndexNoteRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Index a note for semantic search.

    Chunks the note content and generates embeddings.
    This should be called after creating or updating a note.
    """
    service = AISearchService(db)

    try:
        count = await service.index_note(
            note_id=data.note_id,
            user_id=current_user.id,
        )
        return IndexResponse(indexed=count, failed=0)
    except Exception as e:
        logger.error(f"Failed to index note {data.note_id}: {e}")
        return IndexResponse(indexed=0, failed=1)


@router.post("/notes/index/batch", response_model=IndexResponse)
async def index_notes(
    data: IndexNotesRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Index multiple notes for semantic search.

    Processes up to 50 notes in batch.
    """
    service = AISearchService(db)

    indexed = 0
    failed = 0

    for note_id in data.note_ids:
        try:
            count = await service.index_note(
                note_id=note_id,
                user_id=current_user.id,
            )
            if count > 0:
                indexed += 1
        except Exception as e:
            logger.error(f"Failed to index note {note_id}: {e}")
            failed += 1

    return IndexResponse(indexed=indexed, failed=failed)


@router.get("/search/history")
async def get_search_history(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(20, ge=1, le=100),
):
    """Get recent search history.

    Shows past searches and their results.
    """
    service = AISearchService(db)

    history = await service.get_search_history(
        user_id=current_user.id,
        limit=limit,
    )

    from app.schemas.ai_search import SearchHistoryItem

    return [
        SearchHistoryItem(
            id=str(h.id),
            query=h.query,
            search_type=h.search_type,
            results_count=h.results_count,
            created_at=h.created_at,
        )
        for h in history
    ]


@router.post("/config/test", status_code=status.HTTP_204_NO_CONTENT)
async def test_ai_config(
    current_user: CurrentUser,
    db: DBSession,
):
    """Test AI service configuration.

    Verifies that the AI service is accessible and working.
    """
    service = AISearchService(db)

    if service.embedding_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding provider not configured",
        )

    if service.llm_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not configured",
        )

    # Test with a simple embedding
    try:
        results = await service.embedding_provider.embed(["test"])
        if not results or not results[0].embedding:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding provider test failed",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service test failed: {str(e)}",
        )


@router.get("/config")
async def get_ai_config():
    """Get current AI configuration (public info only).

    Returns information about available AI models and providers.
    """
    from app.core.config import get_settings

    settings = get_settings()

    return {
        "embedding_provider": getattr(settings, "AI_EMBEDDING_PROVIDER", "openai"),
        "embedding_model": getattr(settings, "AI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "llm_provider": getattr(settings, "AI_LLM_PROVIDER", "openai"),
        "llm_model": getattr(settings, "AI_LLM_MODEL", "gpt-4o-mini"),
        "service_url": getattr(settings, "AI_SERVICE_URL", None),
        "enabled": bool(settings.AI_SERVICE_URL),
    }
