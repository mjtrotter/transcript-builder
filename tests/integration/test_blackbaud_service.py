"""
Integration Tests for Blackbaud Service

Tests OAuth flow, token management, and API synchronization.
Note: Requires mock server or Blackbaud sandbox credentials for full testing.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from transcript_builder.api.services.blackbaud_service import BlackbaudService


class TestBlackbaudServiceAuth:
    """Tests for Blackbaud OAuth authentication"""

    @pytest.fixture
    def blackbaud_service(self, db_session, test_tenant):
        """Create Blackbaud service instance"""
        return BlackbaudService(
            db=db_session,
            tenant_id=test_tenant.id,
            client_id="test_client_id",
            client_secret="test_client_secret",
            subscription_key="test_subscription_key",
        )

    def test_get_authorization_url(self, blackbaud_service):
        """Test generating OAuth authorization URL"""
        redirect_uri = "https://example.com/callback"
        state = "test_state_123"

        url = blackbaud_service.get_authorization_url(redirect_uri, state)

        assert "oauth2.sky.blackbaud.com/authorization" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https://example.com/callback" in url
        assert "state=test_state_123" in url
        assert "response_type=code" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, blackbaud_service):
        """Test successful token exchange"""
        mock_response = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            result = await blackbaud_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
            )

            assert result["access_token"] == "test_access_token"
            assert blackbaud_service._access_token == "test_access_token"
            assert blackbaud_service._refresh_token == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, blackbaud_service):
        """Test failed token exchange"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=400,
                text="Invalid code",
            )

            with pytest.raises(Exception) as exc_info:
                await blackbaud_service.exchange_code(
                    code="invalid_code",
                    redirect_uri="https://example.com/callback",
                )

            assert "Token exchange failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, blackbaud_service):
        """Test token refresh"""
        blackbaud_service._refresh_token = "old_refresh_token"

        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            result = await blackbaud_service.refresh_access_token()

            assert result["access_token"] == "new_access_token"
            assert blackbaud_service._access_token == "new_access_token"


class TestBlackbaudServiceAPI:
    """Tests for Blackbaud API operations"""

    @pytest.fixture
    def authenticated_service(self, db_session, test_tenant):
        """Create authenticated Blackbaud service"""
        service = BlackbaudService(
            db=db_session,
            tenant_id=test_tenant.id,
            client_id="test_client_id",
            client_secret="test_client_secret",
            subscription_key="test_subscription_key",
        )
        service._access_token = "valid_token"
        return service

    @pytest.mark.asyncio
    async def test_get_students(self, authenticated_service):
        """Test fetching students from Blackbaud"""
        mock_students = {
            "value": [
                {"id": 1001, "first_name": "John", "last_name": "Doe", "grad_year": 2025},
                {"id": 1002, "first_name": "Jane", "last_name": "Smith", "grad_year": 2025},
            ]
        }

        with patch.object(
            authenticated_service, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_students

            students = await authenticated_service.get_students()

            assert len(students) == 2
            assert students[0]["first_name"] == "John"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_student_grades(self, authenticated_service):
        """Test fetching grades for a student"""
        mock_grades = {
            "value": [
                {"course_id": 101, "grade": "A", "credits": 1.0},
                {"course_id": 102, "grade": "B+", "credits": 1.0},
            ]
        }

        with patch.object(
            authenticated_service, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_grades

            grades = await authenticated_service.get_student_grades(1001)

            assert len(grades) == 2
            assert grades[0]["grade"] == "A"

    @pytest.mark.asyncio
    async def test_sync_students(self, authenticated_service):
        """Test syncing students to local database"""
        mock_students = [
            {"id": 1001, "first_name": "John", "last_name": "Doe", "email": "john@test.com"},
        ]

        with patch.object(
            authenticated_service, "get_students", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_students

            result = await authenticated_service.sync_students()

            assert result["total"] == 1
            assert "created" in result
            assert "updated" in result


class TestBlackbaudServiceErrorHandling:
    """Tests for error handling in Blackbaud service"""

    @pytest.fixture
    def service(self, db_session, test_tenant):
        """Create Blackbaud service"""
        return BlackbaudService(
            db=db_session,
            tenant_id=test_tenant.id,
            client_id="test_client_id",
            client_secret="test_client_secret",
            subscription_key="test_subscription_key",
        )

    @pytest.mark.asyncio
    async def test_api_request_without_token(self, service):
        """Test API request without authentication raises error"""
        with pytest.raises(Exception) as exc_info:
            await service._ensure_valid_token()

        assert "Not authenticated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_without_refresh_token(self, service):
        """Test token refresh without refresh token raises error"""
        with pytest.raises(Exception) as exc_info:
            await service.refresh_access_token()

        assert "No refresh token" in str(exc_info.value)
