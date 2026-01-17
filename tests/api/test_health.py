"""
Tests for Health Check Endpoints
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    @pytest.mark.asyncio
    async def test_root_health_check(self, client: AsyncClient):
        """Test root health check endpoint"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_api_health_check(self, client: AsyncClient):
        """Test API health check with detailed status"""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
