"""
Unit tests for FastAPI endpoints.
Tests webhook handling and simulate endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _extract_messages
from app.state import clear_state


@pytest.fixture
def client():
    """Create test client."""
    # Clear any existing state
    clear_state("6281234567890")
    yield TestClient(app)
    clear_state("6281234567890")


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Health check should return ok status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "mulai-gym-chatbot"


class TestSimulateEndpoint:
    """Tests for /simulate endpoint."""

    def test_simulate_hello(self, client):
        """Simulate endpoint should handle hello message."""
        response = client.post("/simulate?phone=6281234567890&message=hello")

        assert response.status_code == 200
        data = response.json()
        assert data["from"] == "6281234567890"
        assert data["message"] == "hello"
        assert "response" in data
        assert len(data["response"]) > 0

    def test_simulate_book(self, client):
        """Simulate endpoint should handle book command."""
        response = client.post("/simulate?phone=6281234567890&message=book")

        assert response.status_code == 200
        data = response.json()
        # Should show classes or member info
        assert "class" in data["response"].lower() or "member" in data["response"].lower()

    def test_simulate_my_bookings(self, client):
        """Simulate endpoint should handle my bookings command."""
        response = client.post("/simulate?phone=6281234567890&message=my%20bookings")

        assert response.status_code == 200
        data = response.json()
        assert "booking" in data["response"].lower() or "book" in data["response"].lower()


class TestWebhookEndpoint:
    """Tests for /webhook endpoint."""

    def test_webhook_empty_payload(self, client):
        """Webhook should handle empty payload."""
        response = client.post("/webhook", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_with_message(self, mock_send, client):
        """Webhook should process valid message payload."""
        mock_send.return_value = {"messages": [{"id": "test"}]}

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "6281234567890",
                            "type": "text",
                            "text": {"body": "hello"}
                        }]
                    }
                }]
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        mock_send.assert_called_once()

    def test_webhook_skips_non_text(self, client):
        """Webhook should skip non-text messages."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "6281234567890",
                            "type": "image",
                        }]
                    }
                }]
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_fallback_format(self, mock_send, client):
        """Webhook should handle fallback message format."""
        mock_send.return_value = {"messages": [{"id": "test"}]}

        payload = {
            "messages": [{
                "from": "6281234567890",
                "type": "text",
                "text": {"body": "test"}
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_skips_missing_phone(self, mock_send, client):
        """Webhook should skip messages without phone number."""
        payload = {
            "messages": [{
                "type": "text",
                "text": {"body": "test"}
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        mock_send.assert_not_called()

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_skips_empty_text(self, mock_send, client):
        """Webhook should skip messages without text body."""
        payload = {
            "messages": [{
                "from": "6281234567890",
                "type": "text",
                "text": {}
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        mock_send.assert_not_called()

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_processes_multiple_messages(self, mock_send, client):
        """Webhook should process multiple messages."""
        mock_send.return_value = {"messages": [{"id": "test"}]}

        payload = {
            "messages": [
                {"from": "6281234567890", "type": "text", "text": {"body": "hello"}},
                {"from": "6281234567891", "type": "text", "text": {"body": "book"}},
            ]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert mock_send.call_count == 2

        clear_state("6281234567891")


class TestTestSendEndpoint:
    """Tests for /test-send endpoint."""

    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_test_send_with_phone_configured(self, mock_send, client):
        """Test send should work when phone is configured."""
        mock_send.return_value = {"messages": [{"id": "test"}]}

        with patch("app.main.get_settings") as mock_settings:
            mock_settings.return_value.my_phone_number = "6281234567890"

            response = client.get("/test-send")
            assert response.status_code == 200
            assert response.json()["status"] == "sent"
            mock_send.assert_called_once()

    def test_test_send_without_phone_configured(self, client):
        """Test send should return error when phone not configured."""
        with patch("app.main.get_settings") as mock_settings:
            mock_settings.return_value.my_phone_number = ""

            response = client.get("/test-send")
            assert response.status_code == 200
            assert "error" in response.json()


class TestExtractMessages:
    """Tests for _extract_messages helper function."""

    def test_extracts_from_standard_payload(self):
        """Should extract messages from standard 360dialog payload."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [
                            {"from": "123", "text": {"body": "test"}}
                        ]
                    }
                }]
            }]
        }
        messages = _extract_messages(payload)
        assert len(messages) == 1
        assert messages[0]["from"] == "123"

    def test_extracts_from_multiple_entries(self):
        """Should extract messages from multiple entries."""
        payload = {
            "entry": [
                {"changes": [{"value": {"messages": [{"id": 1}]}}]},
                {"changes": [{"value": {"messages": [{"id": 2}]}}]},
            ]
        }
        messages = _extract_messages(payload)
        assert len(messages) == 2

    def test_extracts_from_multiple_changes(self):
        """Should extract messages from multiple changes."""
        payload = {
            "entry": [{
                "changes": [
                    {"value": {"messages": [{"id": 1}]}},
                    {"value": {"messages": [{"id": 2}]}},
                ]
            }]
        }
        messages = _extract_messages(payload)
        assert len(messages) == 2

    def test_falls_back_to_top_level_messages(self):
        """Should use top-level messages as fallback."""
        payload = {
            "messages": [{"id": 1}, {"id": 2}]
        }
        messages = _extract_messages(payload)
        assert len(messages) == 2

    def test_handles_empty_payload(self):
        """Should return empty list for empty payload."""
        messages = _extract_messages({})
        assert messages == []

    def test_handles_missing_keys(self):
        """Should handle missing keys gracefully."""
        payload = {"entry": [{"changes": [{}]}]}
        messages = _extract_messages(payload)
        assert messages == []


class TestSimulateEndpointEdgeCases:
    """Additional tests for simulate endpoint."""

    def test_simulate_cancel(self, client):
        """Simulate endpoint should handle cancel command."""
        # First start a flow
        client.post("/simulate?phone=6281234567890&message=book")

        # Then cancel
        response = client.post("/simulate?phone=6281234567890&message=cancel")
        assert response.status_code == 200
        assert "no worries" in response.json()["response"].lower()

    def test_simulate_unknown_command(self, client):
        """Simulate endpoint should show help for unknown commands."""
        response = client.post("/simulate?phone=6281234567890&message=xyz123")

        assert response.status_code == 200
        data = response.json()
        # Should return help message
        assert "book" in data["response"].lower()

    def test_simulate_preserves_state_across_calls(self, client):
        """State should persist across simulate calls."""
        # Start booking
        response1 = client.post("/simulate?phone=6281234567890&message=book")
        assert "class" in response1.json()["response"].lower()

        # Select class (state should be preserved)
        response2 = client.post("/simulate?phone=6281234567890&message=1")
        # Should either book or show waitlist, not return help
        data = response2.json()["response"].lower()
        assert "all set" in data or "waitlist" in data or "booked" in data


class TestWebhookErrorHandling:
    """Tests for webhook error handling."""

    def test_webhook_handles_invalid_json(self, client):
        """Webhook should handle invalid JSON gracefully."""
        response = client.post(
            "/webhook",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        # Webhook catches JSON decode error and returns 500
        assert response.status_code == 500

    @patch("app.main.handle_message", new_callable=AsyncMock)
    @patch("app.main.send_text_message", new_callable=AsyncMock)
    def test_webhook_propagates_handler_error(self, mock_send, mock_handle, client):
        """Webhook should handle errors from message handler."""
        mock_handle.side_effect = Exception("Handler error")

        payload = {
            "messages": [{
                "from": "6281234567890",
                "type": "text",
                "text": {"body": "test"}
            }]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 500
