"""AI Search and RAG service."""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logger import get_logger
from app.models.ai_search import DocumentChunk, SearchHistory
from app.models.note import Note

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding operation."""

    embedding: list[float]
    model: str
    dimensions: int


@dataclass
class SearchResult:
    """Semantic search result."""

    note_id: str
    chunk_id: str
    title: str
    content: str
    score: float
    highlights: list[str]


@dataclass
class AISummary:
    """AI summary result."""

    summary: str
    key_points: list[str]
    model: str
    tokens_used: int


@dataclass
class AIAnswer:
    """AI Q&A result."""

    answer: str
    sources: list[dict[str, Any]]
    model: str
    confidence: float


class EmbeddingProvider:
    """Base class for embedding providers."""

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings

        Returns:
            list[EmbeddingResult]: Embedding results
        """
        raise NotImplementedError


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model: Model name
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.dimensions = 1536 if model == "text-embedding-3-small" else 3072

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings using OpenAI API.

        Args:
            texts: List of text strings

        Returns:
            list[EmbeddingResult]: Embedding results
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data["data"]:
            results.append(
                EmbeddingResult(
                    embedding=item["embedding"],
                    model=self.model,
                    dimensions=self.dimensions,
                )
            )
        return results


class OllamaEmbedding(EmbeddingProvider):
    """Ollama embedding provider (local)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        """Initialize Ollama embedding provider.

        Args:
            base_url: Ollama API base URL
            model: Model name
        """
        self.base_url = base_url
        self.model = model

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings using Ollama API.

        Args:
            texts: List of text strings

        Returns:
            list[EmbeddingResult]: Embedding results
        """
        results = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                data = response.json()

                results.append(
                    EmbeddingResult(
                        embedding=data["embedding"],
                        model=self.model,
                        dimensions=len(data["embedding"]),
                    )
                )
        return results


class LLMProvider:
    """Base class for LLM providers."""

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            str: Generated text
        """
        raise NotImplementedError


class OpenAILLM(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize OpenAI LLM provider.

        Args:
            api_key: OpenAI API key
            model: Model name
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate completion using OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            str: Generated text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]


class OllamaLLM(LLMProvider):
    """Ollama LLM provider (local)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ):
        """Initialize Ollama LLM provider.

        Args:
            base_url: Ollama API base URL
            model: Model name
        """
        self.base_url = base_url
        self.model = model

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate completion using Ollama API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            str: Generated text
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt or "",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        return data.get("response", "")


class AISearchService:
    """Service for AI-powered search and RAG operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize AI search service.

        Args:
            db: Database session
        """
        self.db = db

        # Initialize embedding provider
        self.embedding_provider: EmbeddingProvider | None = None
        self._init_embedding_provider()

        # Initialize LLM provider
        self.llm_provider: LLMProvider | None = None
        self._init_llm_provider()

    def _init_embedding_provider(self) -> None:
        """Initialize embedding provider based on settings."""
        if not settings.AI_SERVICE_URL:
            logger.warning("AI service URL not configured, embedding features disabled")
            return

        provider_type = getattr(settings, "AI_EMBEDDING_PROVIDER", "openai").lower()

        if provider_type == "ollama":
            self.embedding_provider = OllamaEmbedding(
                base_url=settings.AI_SERVICE_URL,
                model=getattr(settings, "AI_EMBEDDING_MODEL", "nomic-embed-text"),
            )
        else:  # OpenAI-compatible
            self.embedding_provider = OpenAIEmbedding(
                api_key=getattr(settings, "AI_API_KEY", ""),
                model=getattr(settings, "AI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )

    def _init_llm_provider(self) -> None:
        """Initialize LLM provider based on settings."""
        if not settings.AI_SERVICE_URL:
            logger.warning("AI service URL not configured, LLM features disabled")
            return

        provider_type = getattr(settings, "AI_LLM_PROVIDER", "openai").lower()

        if provider_type == "ollama":
            self.llm_provider = OllamaLLM(
                base_url=settings.AI_SERVICE_URL,
                model=getattr(settings, "AI_LLM_MODEL", "llama3.2"),
            )
        else:  # OpenAI-compatible
            self.llm_provider = OpenAILLM(
                api_key=getattr(settings, "AI_API_KEY", ""),
                model=getattr(settings, "AI_LLM_MODEL", "gpt-4o-mini"),
            )

    async def index_note(
        self,
        note_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> int:
        """Index a note for semantic search.

        Chunks the note content and generates embeddings.

        Args:
            note_id: Note ID
            user_id: User ID

        Returns:
            int: Number of chunks created
        """
        if self.embedding_provider is None:
            logger.warning("Embedding provider not available")
            return 0

        # Get note
        query = select(Note).where(
            and_(
                Note.id == note_id,
                Note.user_id == user_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(query)
        note = result.scalar_one_or_none()

        if note is None:
            logger.warning(f"Note {note_id} not found for indexing")
            return 0

        # Delete existing chunks
        await self.db.execute(
            select(DocumentChunk).where(
                and_(
                    DocumentChunk.note_id == note_id,
                    DocumentChunk.user_id == user_id,
                )
            )
        )
        await self.db.execute(
            text("DELETE FROM document_chunks WHERE note_id = :note_id AND user_id = :user_id"),
            {"note_id": note_id, "user_id": user_id},
        )

        # Chunk content (simple chunking by paragraph)
        chunks = self._chunk_text(note.content)

        if not chunks:
            logger.info(f"No chunks created for note {note_id}")
            return 0

        # Generate embeddings
        try:
            embedding_results = await self.embedding_provider.embed(chunks)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return 0

        # Store chunks
        for i, (chunk, embedding_result) in enumerate(zip(chunks, embedding_results)):
            # Convert embedding to array for pgvector
            embedding_array = "{" + ",".join(map(str, embedding_result.embedding)) + "}"

            chunk_record = DocumentChunk(
                note_id=note_id,
                user_id=user_id,
                content=chunk,
                chunk_index=i,
                # Store as array string for pgvector
                embedding=embedding_result.embedding,
            )
            self.db.add(chunk_record)

        await self.db.commit()

        logger.info(f"Indexed note {note_id} with {len(chunks)} chunks")
        return len(chunks)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Split text into chunks for embedding.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks

        Returns:
            list[str]: List of text chunks
        """
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 1 <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def semantic_search(
        self,
        query: str,
        user_id: str | uuid.UUID,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Perform semantic search using vector similarity.

        Args:
            query: Search query
            user_id: User ID
            limit: Max results

        Returns:
            list[SearchResult]: Search results
        """
        if self.embedding_provider is None:
            logger.warning("Embedding provider not available")
            return []

        # Generate query embedding
        try:
            embedding_results = await self.embedding_provider.embed([query])
            query_embedding = embedding_results[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # Convert to pgvector format
        embedding_array = "[" + ",".join(map(str, query_embedding)) + "]"

        # Perform vector similarity search
        # Using cosine distance (1 - cosine_similarity)
        sql_query = text("""
            SELECT
                dc.note_id,
                dc.id as chunk_id,
                n.title,
                dc.content,
                1 - (dc.embedding <=> :embedding::vector) as score
            FROM document_chunks dc
            JOIN notes n ON n.id = dc.note_id
            WHERE dc.user_id = :user_id
                AND n.is_deleted = false
            ORDER BY dc.embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self.db.execute(
            sql_query,
            {
                "embedding": embedding_array,
                "user_id": user_id,
                "limit": limit,
            },
        )

        results = []
        for row in result:
            results.append(
                SearchResult(
                    note_id=str(row.note_id),
                    chunk_id=str(row.chunk_id),
                    title=row.title,
                    content=row.content,
                    score=float(row.score),
                    highlights=self._extract_highlights(query, row.content),
                )
            )

        return results

    def _extract_highlights(self, query: str, content: str, max_length: int = 200) -> list[str]:
        """Extract relevant highlights from content.

        Args:
            query: Search query
            content: Content to search
            max_length: Max highlight length

        Returns:
            list[str]: List of highlights
        """
        # Simple keyword matching highlight
        query_words = set(query.lower().split())
        sentences = content.split(".")

        highlights = []
        for sentence in sentences[:5]:  # Max 5 highlights
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in query_words):
                highlight = sentence.strip()[:max_length]
                if len(sentence.strip()) > max_length:
                    highlight += "..."
                highlights.append(highlight)
                if len(highlights) >= 3:
                    break

        return highlights

    async def summarize_note(
        self,
        note_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> AISummary | None:
        """Generate AI summary for a note.

        Args:
            note_id: Note ID
            user_id: User ID

        Returns:
            AISummary | None: Generated summary
        """
        if self.llm_provider is None:
            logger.warning("LLM provider not available")
            return None

        # Get note
        query = select(Note).where(
            and_(
                Note.id == note_id,
                Note.user_id == user_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(query)
        note = result.scalar_one_or_none()

        if note is None:
            return None

        # Generate summary
        system_prompt = """You are a helpful assistant that summarizes notes concisely.
Provide a brief summary (2-3 sentences) and extract 3-5 key bullet points."""

        user_prompt = f"""Please summarize the following note:

Title: {note.title}

Content:
{note.content}

Respond in the following format:
SUMMARY: [Your summary here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
"""

        try:
            response = await self.llm_provider.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=500,
            )

            # Parse response
            summary, key_points = self._parse_summary_response(response)

            return AISummary(
                summary=summary,
                key_points=key_points,
                model=self.llm_provider.model if self.llm_provider else "unknown",
                tokens_used=0,  # Not tracking tokens for now
            )

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    def _parse_summary_response(self, response: str) -> tuple[str, list[str]]:
        """Parse summary response from LLM.

        Args:
            response: LLM response text

        Returns:
            tuple: (summary, key_points)
        """
        lines = response.split("\n")

        summary = ""
        key_points = []
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith("SUMMARY:"):
                current_section = "summary"
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("KEY POINTS:"):
                current_section = "points"
            elif line.startswith("-") and current_section == "points":
                key_points.append(line.lstrip("-").strip())
            elif current_section == "summary" and line:
                summary += " " + line

        return summary.strip(), key_points

    async def answer_question(
        self,
        question: str,
        user_id: str | uuid.UUID,
        note_ids: list[str | uuid.UUID] | None = None,
    ) -> AIAnswer | None:
        """Answer a question using RAG.

        Args:
            question: User question
            user_id: User ID
            note_ids: Optional list of note IDs to search

        Returns:
            AIAnswer | None: Generated answer
        """
        if self.llm_provider is None or self.embedding_provider is None:
            logger.warning("AI providers not available")
            return None

        # Search for relevant chunks
        if note_ids:
            # Search specific notes
            chunks = await self._search_notes(question, user_id, note_ids)
        else:
            # Semantic search
            search_results = await self.semantic_search(question, user_id, limit=5)
            chunks = [r.content for r in search_results]

        if not chunks:
            return AIAnswer(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                model=self.llm_provider.model if self.llm_provider else "unknown",
                confidence=0.0,
            )

        # Build context
        context = "\n\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(chunks)])

        # Generate answer
        system_prompt = """You are a helpful assistant that answers questions based on the provided context.
Use only the information from the context. If the answer is not in the context, say so."""

        user_prompt = f"""Context:
{context}

Question: {question}

Provide a concise answer based on the context. Cite the source number [1], [2], etc. when referencing information.
"""

        try:
            response = await self.llm_provider.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=800,
            )

            # Extract sources
            sources = []
            for i, chunk in enumerate(chunks[:3]):
                sources.append({
                    "chunk_id": str(i),
                    "preview": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                })

            return AIAnswer(
                answer=response,
                sources=sources,
                model=self.llm_provider.model if self.llm_provider else "unknown",
                confidence=0.8,  # Simplified confidence
            )

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return None

    async def _search_notes(
        self,
        query: str,
        user_id: str | uuid.UUID,
        note_ids: list[str | uuid.UUID],
    ) -> list[str]:
        """Search within specific notes.

        Args:
            query: Search query
            user_id: User ID
            note_ids: Note IDs to search

        Returns:
            list[str]: Relevant chunks
        """
        # Get notes
        query_obj = select(Note).where(
            and_(
                Note.id.in_(note_ids),
                Note.user_id == user_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(query_obj)
        notes = result.scalars().all()

        # Simple keyword matching
        chunks = []
        query_lower = query.lower()

        for note in notes:
            # Search in content
            if query_lower in note.content.lower():
                # Find relevant paragraph
                for para in note.content.split("\n\n"):
                    if query_lower in para.lower():
                        chunks.append(para.strip())
                        if len(chunks) >= 3:
                            break

            if len(chunks) >= 3:
                break

        return chunks

    async def record_search(
        self,
        user_id: str | uuid.UUID,
        query: str,
        search_type: str,
        results_count: int,
        duration_ms: int,
    ) -> SearchHistory:
        """Record search in history.

        Args:
            user_id: User ID
            query: Search query
            search_type: Type of search
            results_count: Number of results
            duration_ms: Search duration

        Returns:
            SearchHistory: Created history record
        """
        history = SearchHistory(
            user_id=user_id,
            query=query,
            search_type=search_type,
            results_count=results_count,
            search_duration_ms=duration_ms,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_search_history(
        self,
        user_id: str | uuid.UUID,
        limit: int = 50,
    ) -> list[SearchHistory]:
        """Get user's search history.

        Args:
            user_id: User ID
            limit: Max results

        Returns:
            list[SearchHistory]: Search history
        """
        query = select(SearchHistory).where(
            SearchHistory.user_id == user_id
        ).order_by(desc(SearchHistory.created_at)).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
