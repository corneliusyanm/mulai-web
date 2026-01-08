"""
Unit tests for gym_api module.
Tests API client with mocked HTTP responses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.gym_api import (
    get_available_classes,
    get_member_by_phone,
    book_class,
    join_waitlist,
    cancel_booking,
    get_my_bookings,
)


@pytest.fixture
def mock_settings_real_api():
    """Mock settings to use real API (not mock data)."""
    settings = MagicMock()
    settings.use_mock_data = False
    settings.gym_api_base_url = "https://api.example.com"
    settings.gym_api_key = "test-api-key"
    return settings


class TestGetAvailableClasses:
    """Tests for get_available_classes function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True
            classes = await get_available_classes()

            assert isinstance(classes, list)
            assert len(classes) > 0

    @pytest.mark.asyncio
    async def test_calls_real_api_when_configured(self, mock_settings_real_api):
        """Should call real API when use_mock_data is False."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "class_name": "Test Class"}
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            classes = await get_available_classes()

            assert classes == [{"id": 1, "class_name": "Test Class"}]

    @pytest.mark.asyncio
    async def test_sends_correct_headers(self, mock_settings_real_api):
        """Should send X-API-Key header."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await get_available_classes()

            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs["headers"]["X-API-Key"] == "test-api-key"


class TestGetMemberByPhone:
    """Tests for get_member_by_phone function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True
            member = await get_member_by_phone("6281234567890")

            assert member is not None
            assert "name" in member

    @pytest.mark.asyncio
    async def test_returns_none_for_404(self, mock_settings_real_api):
        """Should return None when API returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            member = await get_member_by_phone("6280000000000")

            assert member is None

    @pytest.mark.asyncio
    async def test_returns_member_on_success(self, mock_settings_real_api):
        """Should return member data on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "John Doe"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            member = await get_member_by_phone("6281234567890")

            assert member == {"id": 1, "name": "John Doe"}

    @pytest.mark.asyncio
    async def test_sends_phone_as_query_param(self, mock_settings_real_api):
        """Should send phone as query parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1}
        mock_response.raise_for_status = MagicMock()

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            await get_member_by_phone("6281234567890")

            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs["params"]["phone"] == "6281234567890"


class TestBookClass:
    """Tests for book_class function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True

            # Need to get a real class ID from mock data
            from app.mock_data import get_mock_classes
            classes = get_mock_classes()
            open_class = next(c for c in classes if c["status"] == "OPEN")

            result = await book_class(9999, open_class["id"])
            assert "success" in result

    @pytest.mark.asyncio
    async def test_calls_real_api_with_payload(self, mock_settings_real_api):
        """Should call real API with correct payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await book_class(1, 100)

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs["json"]["member_id"] == 1
            assert call_kwargs.kwargs["json"]["class_instance_id"] == 100


class TestJoinWaitlist:
    """Tests for join_waitlist function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True

            from app.mock_data import get_mock_classes
            classes = get_mock_classes()

            result = await join_waitlist(8888, classes[0]["id"])
            assert "success" in result

    @pytest.mark.asyncio
    async def test_calls_real_api(self, mock_settings_real_api):
        """Should call real waitlist API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "message": "Added"}

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await join_waitlist(1, 100)

            assert result["success"] is True
            call_kwargs = mock_post.call_args
            assert "/waitlist/" in call_kwargs.args[0]


class TestCancelBooking:
    """Tests for cancel_booking function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True

            from app.mock_data import get_mock_classes, mock_book_class
            classes = get_mock_classes()
            open_class = next(c for c in classes if c["status"] == "OPEN")
            mock_book_class(7777, open_class["id"])

            result = await cancel_booking(7777, open_class["id"])
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_calls_real_api(self, mock_settings_real_api):
        """Should call real cancel API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await cancel_booking(1, 100)

            call_kwargs = mock_post.call_args
            assert "/cancel/" in call_kwargs.args[0]


class TestGetMyBookings:
    """Tests for get_my_bookings function."""

    @pytest.mark.asyncio
    async def test_uses_mock_data_when_configured(self):
        """Should use mock data when use_mock_data is True."""
        with patch("app.gym_api.get_settings") as mock_settings:
            mock_settings.return_value.use_mock_data = True
            bookings = await get_my_bookings(1)

            assert isinstance(bookings, list)

    @pytest.mark.asyncio
    async def test_calls_real_api(self, mock_settings_real_api):
        """Should call real my-bookings API."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "class_name": "Test"}]
        mock_response.raise_for_status = MagicMock()

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await get_my_bookings(1)

            assert result == [{"id": 1, "class_name": "Test"}]
            call_kwargs = mock_get.call_args
            assert call_kwargs.kwargs["params"]["member_id"] == 1


class TestAPIErrorHandling:
    """Tests for API error handling."""

    @pytest.mark.asyncio
    async def test_get_classes_raises_on_http_error(self, mock_settings_real_api):
        """Should raise on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=MagicMock()
        )

        with patch("app.gym_api.get_settings", return_value=mock_settings_real_api), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await get_available_classes()
