"""AI Search API tests."""
import pytest
from unittest.mock import AsyncMock, patch


class TestSemanticSearch:
    """Tests for semantic search endpoint."""

    async def test_semantic_search_no_provider(self, authenticated_client: AsyncClient):
        """Test semantic search when AI provider is not configured."""
        with patch("app.services.ai_search.AISearchService.embedding_provider", None):
            response = await authenticated_client.post(
                "/api/v1/ai/search/semantic",
                json={"query": "test query", "limit": 10},
            )
            # Should return empty results rather than error
            assert response.status_code == 200
            assert response.json()["results"] == []

    async def test_semantic_search_invalid_query(self, authenticated_client: AsyncClient):
        """Test semantic search with invalid query."""
        response = await authenticated_client.post(
            "/api/v1/ai/search/semantic",
            json={"query": "", "limit": 10},
        )
        assert response.status_code == 422


class TestNoteIndexing:
    """Tests for note indexing endpoints."""

    async def test_index_note(self, authenticated_client: AsyncClient):
        """Test indexing a single note."""
        # Create a note first
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Test Note", "content": "Test content for indexing"},
        )
        note_id = note_response.json()["id"]

        # Index the note (will fail if no AI provider, but should handle gracefully)
        with patch("app.services.ai_search.AISearchService.embedding_provider", None):
            response = await authenticated_client.post(
                "/api/v1/ai/notes/index",
                json={"note_id": note_id},
            )
            # Should handle missing provider gracefully
            assert response.status_code in [200, 503]

    async def test_batch_index_notes(self, authenticated_client: AsyncClient):
        """Test batch indexing multiple notes."""
        # Create notes
        note_ids = []
        for i in range(3):
            note_response = await authenticated_client.post(
                "/api/v1/notes",
                json={"title": f"Note {i}", "content": f"Content {i}"},
            )
            note_ids.append(note_response.json()["id"])

        # Batch index
        with patch("app.services.ai_search.AISearchService.embedding_provider", None):
            response = await authenticated_client.post(
                "/api/v1/ai/notes/index/batch",
                json={"note_ids": note_ids},
            )
            # Should handle missing provider
            assert response.status_code in [200, 503]


class TestAISummary:
    """Tests for AI summary endpoint."""

    async def test_summarize_note_no_provider(self, authenticated_client: AsyncClient):
        """Test summarizing a note when AI provider is not configured."""
        # Create a note
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Long Note", "content": "A very long content..."},
        )
        note_id = note_response.json()["id"]

        # Try to summarize
        with patch("app.services.ai_search.AISearchService.llm_provider", None):
            response = await authenticated_client.post(f"/api/v1/ai/notes/{note_id}/summarize")
            assert response.status_code == 503


class TestAIQuestionAnswer:
    """Tests for AI Q&A endpoint."""

    async def test_ask_question_no_provider(self, authenticated_client: AsyncClient):
        """Test asking a question when AI provider is not configured."""
        with patch("app.services.ai_search.AISearchService.llm_provider", None):
            response = await authenticated_client.post(
                "/api/v1/ai/qa",
                json={"question": "What is this about?"},
            )
            assert response.status_code == 503

    async def test_ask_question_with_notes(self, authenticated_client: AsyncClient):
        """Test asking a question about specific notes."""
        # Create notes
        note_ids = []
        for i in range(2):
            note_response = await authenticated_client.post(
                "/api/v1/notes",
                json={"title": f"Topic {i}", "content": f"Information about topic {i}"},
            )
            note_ids.append(note_response.json()["id"])

        with patch("app.services.ai_search.AISearchService.llm_provider", None):
            response = await authenticated_client.post(
                "/api/v1/ai/qa",
                json={"question": "What is topic 1?", "note_ids": note_ids},
            )
            assert response.status_code == 503


class TestAIConfig:
    """Tests for AI configuration endpoints."""

    async def test_get_ai_config(self, authenticated_client: AsyncClient):
        """Test getting AI configuration."""
        response = await authenticated_client.get("/api/v1/ai/config")
        assert response.status_code == 200
        data = response.json()
        assert "embedding_provider" in data
        assert "llm_provider" in data
        assert "enabled" in data

    async def test_ai_config_no_provider(self, authenticated_client: AsyncClient):
        """Test AI config when providers are not configured."""
        with patch(
            "app.services.ai_search.AISearchService.embedding_provider",
            None,
        ):
            response = await authenticated_client.post("/api/v1/ai/config/test")
            assert response.status_code == 503


class TestSearchHistory:
    """Tests for search history endpoint."""

    async def test_get_search_history(self, authenticated_client: AsyncClient):
        """Test getting search history."""
        response = await authenticated_client.get("/api/v1/ai/search/history")
        assert response.status_code == 200
        # Should return empty list initially
        assert isinstance(response.json(), list)
