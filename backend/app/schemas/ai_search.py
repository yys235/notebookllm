"""AI Search and RAG related schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    """Schema for semantic search request."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Max results")


class SemanticSearchResult(BaseModel):
    """Schema for semantic search result."""

    note_id: str = Field(..., description="Note ID")
    chunk_id: str = Field(..., description="Chunk ID")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Relevant content chunk")
    score: float = Field(..., ge=0, le=1, description="Similarity score")
    highlights: list[str] = Field(default_factory=list, description="Highlighted excerpts")


class SemanticSearchResponse(BaseModel):
    """Schema for semantic search response."""

    query: str = Field(..., description="Original query")
    results: list[SemanticSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total results found")


class AISummaryResponse(BaseModel):
    """Schema for AI summary response."""

    summary: str = Field(..., description="AI-generated summary")
    key_points: list[str] = Field(..., description="Key bullet points")
    model: str = Field(..., description="AI model used")


class AIAnswerRequest(BaseModel):
    """Schema for AI Q&A request."""

    question: str = Field(..., min_length=1, max_length=500, description="Question")
    note_ids: list[str] | None = Field(None, description="Optional note IDs to search")


class AIAnswerResponse(BaseModel):
    """Schema for AI Q&A response."""

    answer: str = Field(..., description="AI-generated answer")
    sources: list[dict] = Field(..., description="Source chunks")
    model: str = Field(..., description="AI model used")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")


class IndexNoteRequest(BaseModel):
    """Schema for indexing a note."""

    note_id: str = Field(..., description="Note ID to index")


class IndexNotesRequest(BaseModel):
    """Schema for batch indexing notes."""

    note_ids: list[str] = Field(..., min_items=1, max_items=50, description="Note IDs to index")


class IndexResponse(BaseModel):
    """Schema for index response."""

    indexed: int = Field(..., description="Number of notes indexed")
    failed: int = Field(..., description="Number of notes that failed")


class AIModelConfig(BaseModel):
    """Schema for AI model configuration."""

    embedding_provider: Literal["openai", "ollama"] = Field(
        default="openai", description="Embedding provider"
    )
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    llm_provider: Literal["openai", "ollama"] = Field(
        default="openai", description="LLM provider"
    )
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model")
    service_url: str | None = Field(None, description="Custom service URL for Ollama")


class SearchHistoryItem(BaseModel):
    """Schema for search history item."""

    id: str = Field(..., description="History ID")
    query: str = Field(..., description="Search query")
    search_type: str = Field(..., description="Search type")
    results_count: int = Field(..., description="Number of results")
    created_at: datetime = Field(..., description="Search timestamp")

    model_config = {"from_attributes": True}
