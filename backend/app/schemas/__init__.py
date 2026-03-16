"""Pydantic schemas for request/response validation."""

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.schemas.note_block import (
    BlockCreate,
    BlockUpdate,
    BlockResponse,
    BlockListResponse,
    BlockType,
    ReorderRequest,
)
from app.schemas.share import ShareLinkCreate, ShareLinkRead
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.ai_search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    AISummaryResponse,
    AIAnswerRequest,
    AIAnswerResponse,
    IndexNoteRequest,
    IndexNotesRequest,
    IndexResponse,
    SearchHistoryItem,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "NoteCreate",
    "NoteRead",
    "NoteUpdate",
    "BlockCreate",
    "BlockUpdate",
    "BlockResponse",
    "BlockListResponse",
    "BlockType",
    "ReorderRequest",
    "ShareLinkCreate",
    "ShareLinkRead",
    "ErrorResponse",
    "PaginatedResponse",
    "SemanticSearchRequest",
    "SemanticSearchResponse",
    "AISummaryResponse",
    "AIAnswerRequest",
    "AIAnswerResponse",
    "IndexNoteRequest",
    "IndexNotesRequest",
    "IndexResponse",
    "SearchHistoryItem",
]
