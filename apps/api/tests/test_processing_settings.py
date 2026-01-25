"""Tests for processing settings endpoints."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    with patch("app.routers.processing._require_auth") as mock:
        mock.return_value = 1  # Return user_id
        yield mock


@pytest.fixture
def mock_auth_api_key():
    """Mock API key authentication (returns -1)."""
    with patch("app.routers.processing._require_auth") as mock:
        mock.return_value = -1  # Return -1 for API key
        yield mock


class TestGlobalProcessingSettings:
    """Tests for global processing settings endpoints."""

    def test_get_processing_settings(self, client, mock_auth_user):
        """Test GET /processing/settings returns global settings."""
        response = client.get(
            "/processing/settings",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields are present
        assert "ai_auto_process_on_upload" in data
        assert "ai_auto_process_skip_existing" in data
        assert "llm_primary_provider" in data
        assert "llm_fallback_provider" in data
        assert "tts_primary_provider" in data
        assert "tts_fallback_provider" in data
        assert "queue_max_concurrency" in data
        assert "vocabulary_max_words_per_module" in data
        assert "audio_generation_languages" in data
        assert "audio_generation_concurrency" in data

    def test_update_processing_settings(self, client, mock_auth_user):
        """Test PUT /processing/settings updates global settings."""
        update_data = {
            "ai_auto_process_on_upload": False,
            "llm_primary_provider": "gemini",
        }

        response = client.put(
            "/processing/settings",
            headers={"Authorization": "Bearer test-token"},
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ai_auto_process_on_upload"] is False
        assert data["llm_primary_provider"] == "gemini"

    def test_update_settings_requires_user_auth(self, client, mock_auth_api_key):
        """Test PUT /processing/settings rejects API key authentication."""
        update_data = {
            "ai_auto_process_on_upload": False,
        }

        response = client.put(
            "/processing/settings",
            headers={"Authorization": "Bearer api-key-token"},
            json=update_data,
        )

        assert response.status_code == 403
        assert "user authentication" in response.json()["detail"].lower()

    def test_update_settings_partial_update(self, client, mock_auth_user):
        """Test PUT /processing/settings allows partial updates."""
        # Only update one field
        update_data = {
            "queue_max_concurrency": 5,
        }

        response = client.put(
            "/processing/settings",
            headers={"Authorization": "Bearer test-token"},
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["queue_max_concurrency"] == 5

    def test_get_settings_returns_consistent_types(self, client, mock_auth_user):
        """Test GET /processing/settings returns correct types."""
        response = client.get(
            "/processing/settings",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check types
        assert isinstance(data["ai_auto_process_on_upload"], bool)
        assert isinstance(data["ai_auto_process_skip_existing"], bool)
        assert isinstance(data["llm_primary_provider"], str)
        assert isinstance(data["queue_max_concurrency"], int)
        assert isinstance(data["vocabulary_max_words_per_module"], int)


class TestPublisherProcessingSettingsAuth:
    """Tests for publisher settings authentication."""

    def test_update_publisher_settings_requires_user_auth(
        self, client, mock_auth_api_key
    ):
        """Test PUT /processing/publishers/{id}/settings rejects API key authentication."""
        update_data = {
            "ai_auto_process_enabled": True,
        }

        response = client.put(
            "/processing/publishers/1/settings",
            headers={"Authorization": "Bearer api-key-token"},
            json=update_data,
        )

        assert response.status_code == 403
        assert "user authentication" in response.json()["detail"].lower()
