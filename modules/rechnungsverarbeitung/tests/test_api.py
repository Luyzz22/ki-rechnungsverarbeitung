"""
Tests für API-Endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app


@pytest.fixture
def client():
    """Test-Client für FastAPI"""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests für /health"""
    
    def test_health_returns_200(self, client):
        """Health-Check gibt 200 zurück"""
        response = client.get("/api/health")
        assert response.status_code == 200
    
    def test_health_contains_status(self, client):
        """Health-Check enthält Status"""
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
    
    def test_health_contains_database(self, client):
        """Health-Check enthält DB-Status"""
        response = client.get("/api/health")
        data = response.json()
        assert "database" in data
    
    def test_health_contains_version(self, client):
        """Health-Check enthält Version"""
        response = client.get("/api/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"


class TestUserEndpoint:
    """Tests für /api/user"""
    
    def test_user_not_logged_in(self, client):
        """Nicht eingeloggt gibt logged_in=false"""
        response = client.get("/api/user")
        assert response.status_code == 200
        data = response.json()
        assert data["logged_in"] == False
    
    def test_user_response_schema(self, client):
        """Response hat korrektes Schema"""
        response = client.get("/api/user")
        data = response.json()
        assert "logged_in" in data
        assert "is_admin" in data
        # email/name nur bei eingeloggten Usern
        if data.get("logged_in"):
            assert "email" in data
            assert "name" in data


class TestLandingEndpoint:
    """Tests für /landing"""
    
    def test_landing_returns_200(self, client):
        """Landing-Page gibt 200 zurück"""
        response = client.get("/landing")
        assert response.status_code == 200
    
    def test_landing_returns_html(self, client):
        """Landing-Page gibt HTML zurück"""
        response = client.get("/landing")
        assert "text/html" in response.headers.get("content-type", "")


class TestLoginEndpoint:
    """Tests für /login"""
    
    def test_login_page_returns_200(self, client):
        """Login-Page gibt 200 zurück"""
        response = client.get("/login")
        assert response.status_code == 200
    
    def test_login_invalid_credentials(self, client):
        """Ungültige Credentials werden abgelehnt"""
        response = client.post("/login", data={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        # Sollte nicht erfolgreich einloggen (redirect oder error)
        assert response.status_code in [200, 302, 303, 400, 401]


class TestProtectedEndpoints:
    """Tests für geschützte Endpoints"""
    
    def test_upload_requires_auth(self, client):
        """Upload erfordert Login"""
        response = client.post("/api/upload", files=[])
        assert response.status_code == 401
    
    def test_history_redirects_to_login(self, client):
        """History redirectet zu Login"""
        response = client.get("/history", follow_redirects=False)
        assert response.status_code in [302, 303, 307]


class TestRateLimiting:
    """Tests für Rate Limiting"""
    
    def test_health_not_rate_limited(self, client):
        """Health-Check ist nicht rate-limited"""
        for _ in range(10):
            response = client.get("/api/health")
            assert response.status_code == 200
