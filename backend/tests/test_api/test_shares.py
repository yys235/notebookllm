"""Share link API tests."""
import pytest
from datetime import datetime, timezone, timedelta


class TestShareLinkCreation:
    """Tests for share link creation."""

    async def test_create_share_link(self, authenticated_client: AsyncClient):
        """Test creating a share link."""
        # Create a note first
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Shareable Note", "content": "Content to share"},
        )
        note_id = note_response.json()["id"]

        # Create share link
        response = await authenticated_client.post(
            "/api/v1/shares",
            json={
                "note_id": note_id,
                "expires_in_hours": 24,
                "max_access_count": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["note_id"] == note_id
        assert data["has_password"] is False
        assert data["max_access_count"] == 10
        assert data["is_active"] is True
        assert data["access_count"] == 0
        assert data["remaining_accesses"] == 10
        assert "token" in data
        assert "share_url" in data

    async def test_create_share_link_with_password(self, authenticated_client: AsyncClient):
        """Test creating a password-protected share link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Protected Note", "content": "Secret content"},
        )
        note_id = note_response.json()["id"]

        response = await authenticated_client.post(
            "/api/v1/shares",
            json={
                "note_id": note_id,
                "password": "secure123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["has_password"] is True

    async def test_create_share_link_nonexistent_note(self, authenticated_client: AsyncClient):
        """Test creating share link for nonexistent note."""
        response = await authenticated_client.post(
            "/api/v1/shares",
            json={
                "note_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 404


class TestShareLinkList:
    """Tests for listing share links."""

    async def test_list_share_links_empty(self, authenticated_client: AsyncClient):
        """Test listing share links when none exist."""
        response = await authenticated_client.get("/api/v1/shares")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_share_links_with_items(self, authenticated_client: AsyncClient):
        """Test listing share links after creating some."""
        # Create note and share links
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        await authenticated_client.post("/api/v1/shares", json={"note_id": note_id})
        await authenticated_client.post("/api/v1/shares", json={"note_id": note_id})

        response = await authenticated_client.get("/api/v1/shares")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_share_links_filter_by_note(self, authenticated_client: AsyncClient):
        """Test filtering share links by note ID."""
        # Create two notes
        note1_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 1", "content": "Content 1"},
        )
        note1_id = note1_response.json()["id"]

        note2_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note 2", "content": "Content 2"},
        )
        note2_id = note2_response.json()["id"]

        # Create share links
        await authenticated_client.post("/api/v1/shares", json={"note_id": note1_id})
        await authenticated_client.post("/api/v1/shares", json={"note_id": note2_id})

        # Filter by note1
        response = await authenticated_client.get(
            f"/api/v1/shares?note_id={note1_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["note_id"] == note1_id


class TestShareLinkAccess:
    """Tests for accessing shared notes."""

    async def test_access_shared_note_no_password(self, authenticated_client: AsyncClient):
        """Test accessing a non-password-protected shared note."""
        # Create note and share link
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Public Note", "content": "Public content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        token = share_response.json()["token"]

        # Access via public endpoint (use new client without auth)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as public_client:
            response = await public_client.post(f"/api/v1/shares/public/{token}/access")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Public Note"
        assert data["content"] == "Public content"

    async def test_access_shared_note_with_password_valid(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test accessing a password-protected note with correct password."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Protected Note", "content": "Secret content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id, "password": "test123"},
        )
        token = share_response.json()["token"]

        # Access with password
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as public_client:
            response = await public_client.post(
                f"/api/v1/shares/public/{token}/access",
                json={"password": "test123"},
            )

        assert response.status_code == 200
        assert response.json()["content"] == "Secret content"

    async def test_access_shared_note_with_password_invalid(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test accessing a password-protected note with wrong password."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Protected Note", "content": "Secret content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id, "password": "correct123"},
        )
        token = share_response.json()["token"]

        # Access with wrong password
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as public_client:
            response = await public_client.post(
                f"/api/v1/shares/public/{token}/access",
                json={"password": "wrong123"},
            )

        assert response.status_code == 401

    async def test_access_expired_link(self, authenticated_client: AsyncClient):
        """Test accessing an expired share link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        # Create link that expires immediately
        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id, "expires_in_hours": -1},  # Already expired
        )
        token = share_response.json()["token"]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as public_client:
            response = await public_client.post(f"/api/v1/shares/public/{token}/access")

        assert response.status_code == 403


class TestShareLinkManagement:
    """Tests for share link management operations."""

    async def test_revoke_share_link(self, authenticated_client: AsyncClient):
        """Test revoking a share link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        link_id = share_response.json()["id"]

        # Revoke
        revoke_response = await authenticated_client.post(f"/api/v1/shares/{link_id}/revoke")
        assert revoke_response.status_code == 200
        assert revoke_response.json()["is_active"] is False

    async def test_reactivate_share_link(self, authenticated_client: AsyncClient):
        """Test reactivating a revoked share link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        link_id = share_response.json()["id"]

        # Revoke then reactivate
        await authenticated_client.post(f"/api/v1/shares/{link_id}/revoke")
        reactivate_response = await authenticated_client.post(
            f"/api/v1/shares/{link_id}/reactivate"
        )

        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_active"] is True

    async def test_delete_share_link(self, authenticated_client: AsyncClient):
        """Test permanently deleting a share link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        link_id = share_response.json()["id"]

        # Delete
        delete_response = await authenticated_client.delete(f"/api/v1/shares/{link_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(f"/api/v1/shares/{link_id}")
        assert get_response.status_code == 404

    async def test_update_share_link(self, authenticated_client: AsyncClient):
        """Test updating share link settings."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        link_id = share_response.json()["id"]

        # Update with password and expiration
        update_response = await authenticated_client.patch(
            f"/api/v1/shares/{link_id}",
            json={
                "password": "newpass123",
                "expires_in_hours": 48,
                "max_access_count": 5,
            },
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["has_password"] is True
        assert data["max_access_count"] == 5


class TestShareLinkInfo:
    """Tests for share link info endpoint."""

    async def test_get_share_link_info_no_password(self, authenticated_client: AsyncClient):
        """Test getting share link info for non-protected link."""
        note_response = await authenticated_client.post(
            "/api/v1/notes",
            json={"title": "Note", "content": "Content"},
        )
        note_id = note_response.json()["id"]

        share_response = await authenticated_client.post(
            "/api/v1/shares",
            json={"note_id": note_id},
        )
        token = share_response.json()["token"]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as public_client:
            response = await public_client.get(f"/api/v1/shares/public/{token}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["has_password"] is False
        assert data["is_valid"] is True
