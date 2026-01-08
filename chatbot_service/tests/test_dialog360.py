"""
Unit tests for dialog360 WhatsApp API client.
Tests message sending and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.dialog360 import send_text_message, Dialog360Error


@pytest.fixture
def mock_settings():
    """Mock settings for dialog360."""
    settings = MagicMock()
    settings.d360_api_key = "test-api-key"
    settings.d360_base_url = "https://waba-sandbox.360dialog.io"
    settings.http_timeout = 30
    return settings


class TestSendTextMessage:
    """Tests for send_text_message function."""

    @pytest.mark.asyncio
    async def test_sends_message_successfully(self, mock_settings):
        """Should send message and return result."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.xxx"}]}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await send_text_message("6281234567890", "Hello!")

            assert "messages" in result
            assert result["messages"][0]["id"] == "wamid.xxx"

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, mock_settings):
        """Should send correct WhatsApp message payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": []}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await send_text_message("6281234567890", "Test message")

            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs["json"]

            assert payload["messaging_product"] == "whatsapp"
            assert payload["to"] == "6281234567890"
            assert payload["type"] == "text"
            assert payload["text"]["body"] == "Test message"

    @pytest.mark.asyncio
    async def test_sends_correct_headers(self, mock_settings):
        """Should send D360-API-KEY header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": []}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await send_text_message("6281234567890", "Test")

            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs["headers"]

            assert headers["D360-API-KEY"] == "test-api-key"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, mock_settings):
        """Should call /v1/messages endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": []}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await send_text_message("6281234567890", "Test")

            call_kwargs = mock_post.call_args
            url = call_kwargs.args[0]
            assert url == "https://waba-sandbox.360dialog.io/v1/messages"


class TestDialog360Errors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_raises_on_api_error(self, mock_settings):
        """Should raise Dialog360Error on API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid phone"}}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(Dialog360Error) as exc_info:
                await send_text_message("invalid", "Test")

            assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_401_unauthorized(self, mock_settings):
        """Should raise Dialog360Error on unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(Dialog360Error):
                await send_text_message("6281234567890", "Test")

    @pytest.mark.asyncio
    async def test_raises_on_500_server_error(self, mock_settings):
        """Should raise Dialog360Error on server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal error"}

        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(Dialog360Error):
                await send_text_message("6281234567890", "Test")

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, mock_settings):
        """Should raise Dialog360Error on timeout."""
        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            with pytest.raises(Dialog360Error) as exc_info:
                await send_text_message("6281234567890", "Test")

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self, mock_settings):
        """Should raise Dialog360Error on connection error."""
        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            with pytest.raises(Dialog360Error) as exc_info:
                await send_text_message("6281234567890", "Test")

            assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_on_request_error(self, mock_settings):
        """Should raise Dialog360Error on generic request error."""
        with patch("app.dialog360.get_settings", return_value=mock_settings), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            with pytest.raises(Dialog360Error):
                await send_text_message("6281234567890", "Test")


class TestDialog360ErrorClass:
    """Tests for Dialog360Error exception class."""

    def test_is_exception(self):
        """Dialog360Error should be an Exception."""
        error = Dialog360Error("test error")
        assert isinstance(error, Exception)

    def test_stores_message(self):
        """Should store error message."""
        error = Dialog360Error("Something went wrong")
        assert str(error) == "Something went wrong"
