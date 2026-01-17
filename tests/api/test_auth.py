"""
Tests for Authentication Endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from transcript_builder.api.database.models import Tenant, User


class TestAuthEndpoints:
    """Tests for authentication endpoints"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test successful login"""
        response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "test@test.com",
                "password": "testpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: User):
        """Test login with invalid credentials"""
        response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "test@test.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "noone@test.com",
                "password": "password",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, test_user: User):
        """Test getting current user info"""
        # First login
        login_response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "test@test.com",
                "password": "testpassword",
            },
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@test.com"
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )

        assert response.status_code == 401
