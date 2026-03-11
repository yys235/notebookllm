"""Authentication API tests."""
import pytest


class TestRegistration:
    """Tests for user registration endpoint."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert data["is_active"] is True

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with duplicate email."""
        # First registration
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user1",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )

        # Duplicate email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "user2",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    async def test_register_password_mismatch(self, client: AsyncClient):
        """Test registration with password mismatch."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "Password123!",
                "confirm_password": "Different123!",
            },
        )
        assert response.status_code == 400
        assert "do not match" in response.json()["detail"]

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "short",
                "confirm_password": "short",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""

    async def test_login_success(self, authenticated_client: AsyncClient):
        """Test successful login."""
        # Authenticated client is already logged in, this test
        # verifies the login flow via conftest
        assert authenticated_client.headers.get("Authorization") is not None

    async def test_login_with_username(self, client: AsyncClient):
        """Test login with username."""
        # Register user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "LoginPass123!",
                "confirm_password": "LoginPass123!",
            },
        )

        # Login with username
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "loginuser", "password": "LoginPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_email(self, client: AsyncClient):
        """Test login with email."""
        # Register user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "emaillogin@example.com",
                "username": "emailuser",
                "password": "EmailPass123!",
                "confirm_password": "EmailPass123!",
            },
        )

        # Login with email
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "emaillogin@example.com", "password": "EmailPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "wrong"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    async def test_refresh_token(self, client: AsyncClient):
        """Test refreshing access token."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "username": "refreshuser",
                "password": "RefreshPass123!",
                "confirm_password": "RefreshPass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "refreshuser", "password": "RefreshPass123!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != refresh_token

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoints."""

    async def test_logout(self, authenticated_client: AsyncClient):
        """Test logout endpoint."""
        # Get refresh token first
        response = await authenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPassword123!"},
        )
        refresh_token = response.json()["refresh_token"]

        # Logout
        response = await authenticated_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 204

        # Try to use the refresh token again
        response = await authenticated_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401


class TestSessionManagement:
    """Tests for session management endpoints."""

    async def test_list_sessions(self, authenticated_client: AsyncClient):
        """Test listing active sessions."""
        response = await authenticated_client.get("/api/v1/auth/sessions")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 1
        # At least one session should be marked as current
        assert any(s["is_current"] for s in sessions)

    async def test_logout_all(self, authenticated_client: AsyncClient):
        """Test logout from all devices."""
        response = await authenticated_client.post("/api/v1/auth/logout-all")
        assert response.status_code == 204

        # Verify all sessions are revoked
        sessions_response = await authenticated_client.get("/api/v1/auth/sessions")
        sessions = sessions_response.json()
        # Should have no active sessions
        assert len(sessions) == 0


class TestPasswordChange:
    """Tests for password change endpoint."""

    async def test_change_password_success(self, authenticated_client: AsyncClient):
        """Test successful password change."""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "TestPassword123!",
                "new_password": "NewPassword456!",
            },
        )
        assert response.status_code == 204

        # Login with new password should work
        login_response = await authenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "NewPassword456!"},
        )
        assert login_response.status_code == 200

    async def test_change_password_wrong_old(self, authenticated_client: AsyncClient):
        """Test password change with wrong old password."""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "WrongPassword",
                "new_password": "NewPassword456!",
            },
        )
        assert response.status_code == 400
        assert "Incorrect" in response.json()["detail"]


class TestGetCurrentUser:
    """Tests for getting current user info."""

    async def test_get_current_user(self, authenticated_client: AsyncClient):
        """Test getting current authenticated user."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "id" in data

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting user without authentication."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
