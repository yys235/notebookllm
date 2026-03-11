"""Notes API tests."""
import pytest
from datetime import datetime


class TestNotesList:
    """Tests for notes list endpoint."""

    async def test_list_notes_empty(self, authenticated_client: AsyncClient):
        """Test listing notes when user has none."""
        response = await authenticated_client.get("/api/v1/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_create_note(self, authenticated_client: AsyncClient):
        """Test creating a new note."""
        response = await authenticated_client.post(
            "/api/v1/notes",
            json={
                "title": "Test Note",
                "content": "This is test content",
                "is_pinned": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Note"
        assert data["content"] == "This is test content"
        assert "id" in data

    async def test_create_pinned_note(self, authenticated_client: AsyncClient):
        """Test creating a pinned note."""
        response = await authenticated_client.post(
            "/api/v1/notes",
            json={
                "title": "Pinned Note",
                "content": "Important content",
                "is_pinned": True,
            },
        )
        assert response.status_code == 201
        assert response.json()["is_pinned"] is True

    async def test_list_notes_with_items(self, authenticated_client: AsyncClient):
        """Test listing notes after creating some."""
        # Create two notes
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 1", "content": "Content 1"},
        )
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 2", "content": "Content 2"},
        )

        response = await authenticated_client.get("/api/v1/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_notes_search(self, authenticated_client: AsyncClient):
        """Test searching notes."""
        # Create notes
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Python Tutorial", "content": "Learn Python programming"},
        )
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "JavaScript Guide", "content": "Learn JS"},
        )

        # Search for "Python"
        response = await authenticated_client.get("/api/v1/notes?search=Python")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Python" in data["items"][0]["title"]

    async def test_list_notes_sorting(self, authenticated_client: AsyncClient):
        """Test sorting notes."""
        # Create notes
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "A Note", "content": "First"},
        )
        await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Z Note", "content": "Last"},
        )

        # Sort by title ascending
        response = await authenticated_client.get("/api/v1/notes?sort_by=title&sort_order=asc")
        assert response.status_code == 200
        items = response.json()["items"]
        assert items[0]["title"] == "A Note"
        assert items[1]["title"] == "Z Note"


class TestNoteOperations:
    """Tests for individual note operations."""

    async def test_get_note(self, authenticated_client: AsyncClient):
        """Test getting a specific note."""
        # Create note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Test Note", "content": "Content"},
        )
        note_id = create_response.json()["id"]

        # Get note
        response = await authenticated_client.get(f"/api/v1/notes/{note_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note_id
        assert data["title"] == "Test Note"

    async def test_update_note(self, authenticated_client: AsyncClient):
        """Test updating a note."""
        # Create note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Original", "content": "Original content"},
        )
        note_id = create_response.json()["id"]

        # Update note
        response = await authenticated_client.patch(
            f"/api/v1/notes/{note_id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["content"] == "Original content"

    async def test_update_note_with_summary(self, authenticated_client: AsyncClient):
        """Test updating a note with change summary."""
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Original", "content": "Content"},
        )
        note_id = create_response.json()["id"]

        response = await authenticated_client.patch(
            f"/api/v1/notes/{note_id}?change_summary=Fixed+typo",
            json={"title": "Corrected"},
        )
        assert response.status_code == 200

    async def test_delete_note_soft(self, authenticated_client: AsyncClient):
        """Test soft deleting a note."""
        # Create note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "To Delete", "content": "Content"},
        )
        note_id = create_response.json()["id"]

        # Delete note (soft delete)
        response = await authenticated_client.delete(f"/api/v1/notes/{note_id}")
        assert response.status_code == 204

        # Verify note is deleted
        response = await authenticated_client.get(f"/api/v1/notes/{note_id}")
        assert response.status_code == 404

    async def test_restore_note(self, authenticated_client: AsyncClient):
        """Test restoring a deleted note."""
        # Create and delete note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Temp", "content": "Content"},
        )
        note_id = create_response.json()["id"]

        await authenticated_client.delete(f"/api/v1/notes/{note_id}")

        # Restore
        response = await authenticated_client.post(f"/api/v1/notes/{note_id}/restore")
        assert response.status_code == 200
        assert response.json()["title"] == "Temp"

    async def test_get_nonexistent_note(self, authenticated_client: AsyncClient):
        """Test getting a note that doesn't exist."""
        response = await authenticated_client.get(
            "/api/v1/notes/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestNoteVersions:
    """Tests for note version history."""

    async def test_get_versions(self, authenticated_client: AsyncClient):
        """Test getting version history."""
        # Create note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Version Test", "content": "V1"},
        )
        note_id = create_response.json()["id"]

        # Update to create new version
        await authenticated_client.patch(
            f"/api/v1/notes/{note_id}",
            json={"content": "V2"},
        )

        # Get versions
        response = await authenticated_client.get(f"/api/v1/notes/{note_id}/versions")
        assert response.status_code == 200
        versions = response.json()
        assert len(versions) == 2  # Initial + update
        assert versions[0]["version_number"] == 2
        assert versions[1]["version_number"] == 1

    async def test_restore_from_version(self, authenticated_client: AsyncClient):
        """Test restoring a note from a specific version."""
        # Create and update note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Original", "content": "Original Content"},
        )
        note_id = create_response.json()["id"]

        await authenticated_client.patch(
            f"/api/v1/notes/{note_id}",
            json={"content": "Modified Content"},
        )

        # Get versions
        versions_response = await authenticated_client.get(f"/api/v1/notes/{note_id}/versions")
        first_version_id = versions_response.json()[-1]["id"]  # First version

        # Restore from first version
        restore_response = await authenticated_client.post(
            f"/api/v1/notes/{note_id}/versions/restore",
            json={"version_id": first_version_id},
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["content"] == "Original Content"


class TestBatchOperations:
    """Tests for batch operations."""

    async def test_batch_update_pin(self, authenticated_client: AsyncClient):
        """Test batch updating note pin status."""
        # Create notes
        note1_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 1", "content": "Content 1"},
        )
        note2_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 2", "content": "Content 2"},
        )

        note_ids = [note1_response.json()["id"], note2_response.json()["id"]]

        # Batch pin
        response = await authenticated_client.post(
            "/api/v1/notes/batch/update",
            json={"note_ids": note_ids, "is_pinned": True},
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 2

    async def test_batch_delete(self, authenticated_client: AsyncClient):
        """Test batch deleting notes."""
        # Create notes
        note1_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 1", "content": "Content 1"},
        )
        note2_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 2", "content": "Content 2"},
        )

        note_ids = [note1_response.json()["id"], note2_response.json()["id"]]

        # Batch delete
        response = await authenticated_client.post(
            "/api/v1/notes/batch/delete",
            json={"note_ids": note_ids},
        )
        assert response.status_code == 200
        assert response.json()["deleted"] == 2


class TestTrashOperations:
    """Tests for trash/deleted notes operations."""

    async def test_list_trash(self, authenticated_client: AsyncClient):
        """Test listing deleted notes."""
        # Create and delete a note
        create_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Deleted Note", "content": "Content"},
        )
        note_id = create_response.json()["id"]
        await authenticated_client.delete(f"/api/v1/notes/{note_id}")

        # List trash
        response = await authenticated_client.get("/api/v1/notes/trash/list")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_empty_trash(self, authenticated_client: AsyncClient):
        """Test permanently deleting all trash."""
        # Create and delete notes
        for i in range(3):
            create_response = await authenticated_client.post(
                "/api/v1/notes",
                json={"title": f"Note {i}", "content": f"Content {i}"},
            )
            await authenticated_client.delete(f"/api/v1/notes/{note_id}")

        # Empty trash
        response = await authenticated_client.delete("/api/v1/notes/trash/empty")
        assert response.status_code == 204

        # Verify trash is empty
        response = await authenticated_client.get("/api/v1/notes/trash/list")
        assert response.json()["total"] == 0
