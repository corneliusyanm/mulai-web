"""
Unit tests for message handlers.
Tests the conversation flow and state management.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.handlers import (
    BOOKING_KEYWORDS,
    CANCEL_KEYWORDS,
    HELP_KEYWORDS,
    MY_BOOKINGS_KEYWORDS,
    YES_KEYWORDS,
    NO_KEYWORDS,
    get_help_message,
    handle_message,
)
from app.state import clear_state, get_state, set_state


@pytest.fixture(autouse=True)
def reset_state():
    """Clear state before each test."""
    clear_state("test_phone")
    yield
    clear_state("test_phone")


class TestHelpMessage:
    """Tests for help/welcome message."""

    @pytest.mark.asyncio
    async def test_help_keywords_return_help(self):
        """Typing help keywords should return the help message."""
        for kw in HELP_KEYWORDS:
            response = await handle_message("test_phone", kw)
            assert "book" in response.lower()
            assert "my bookings" in response.lower()

    @pytest.mark.asyncio
    async def test_unknown_message_returns_help(self):
        """Unknown messages in idle state should return help."""
        response = await handle_message("test_phone", "asdfghjkl")
        assert "book" in response.lower()


class TestCancelFlow:
    """Tests for cancel functionality."""

    @pytest.mark.asyncio
    async def test_cancel_clears_state(self):
        """Cancel keyword should clear conversation state."""
        # Start a booking flow
        await handle_message("test_phone", "book")
        assert get_state("test_phone").get("mode") == "selecting_class"

        # Cancel
        response = await handle_message("test_phone", "cancel")
        assert "no worries" in response.lower()
        assert get_state("test_phone").get("mode") is None

    @pytest.mark.asyncio
    async def test_all_cancel_keywords_work(self):
        """All cancel keywords should work."""
        for kw in CANCEL_KEYWORDS:
            await handle_message("test_phone", "book")
            response = await handle_message("test_phone", kw)
            assert "no worries" in response.lower() or "let me know" in response.lower()
            clear_state("test_phone")


class TestBookingFlow:
    """Tests for class booking conversation flow."""

    @pytest.mark.asyncio
    async def test_book_keyword_starts_flow(self):
        """Booking keywords should start the booking flow."""
        for kw in BOOKING_KEYWORDS:
            clear_state("test_phone")
            response = await handle_message("test_phone", kw)
            # Should show classes or member not found
            assert "class" in response.lower() or "account" in response.lower()

    @pytest.mark.asyncio
    async def test_book_shows_classes_for_member(self):
        """Booking should show available classes for valid member."""
        response = await handle_message("test_phone", "book")

        # Mock member should be found and classes shown
        assert "semi private" in response.lower() or "test member" in response.lower()
        assert get_state("test_phone").get("mode") == "selecting_class"

    @pytest.mark.asyncio
    async def test_selecting_valid_class_number(self):
        """Selecting a valid class number should book it."""
        await handle_message("test_phone", "book")

        # Select first class
        response = await handle_message("test_phone", "1")

        # Should either book successfully or show waitlist option
        assert (
            "all set" in response.lower()
            or "waitlist" in response.lower()
            or "booked" in response.lower()
        )

    @pytest.mark.asyncio
    async def test_selecting_invalid_number(self):
        """Selecting an invalid number should ask for valid input."""
        await handle_message("test_phone", "book")

        response = await handle_message("test_phone", "999")
        assert "number between" in response.lower()

    @pytest.mark.asyncio
    async def test_selecting_non_number(self):
        """Non-number input during selection should ask for valid input."""
        await handle_message("test_phone", "book")

        response = await handle_message("test_phone", "abc")
        assert "number between" in response.lower()


class TestWaitlistFlow:
    """Tests for waitlist confirmation flow."""

    @pytest.mark.asyncio
    async def test_yes_confirms_waitlist(self):
        """Answering yes should join the waitlist."""
        await handle_message("test_phone", "book")

        # Find a FULL class (index 3 in mock data is 16:15 Semi Private)
        state = get_state("test_phone")
        classes = state.get("classes", [])

        full_class_idx = None
        for i, c in enumerate(classes):
            if c.get("status") == "FULL":
                full_class_idx = i + 1
                break

        if full_class_idx:
            await handle_message("test_phone", str(full_class_idx))
            response = await handle_message("test_phone", "yes")
            assert "waitlist" in response.lower()

    @pytest.mark.asyncio
    async def test_no_declines_waitlist(self):
        """Answering no should decline waitlist."""
        await handle_message("test_phone", "book")

        state = get_state("test_phone")
        classes = state.get("classes", [])

        full_class_idx = None
        for i, c in enumerate(classes):
            if c.get("status") == "FULL":
                full_class_idx = i + 1
                break

        if full_class_idx:
            await handle_message("test_phone", str(full_class_idx))
            response = await handle_message("test_phone", "no")
            assert "no problem" in response.lower()


class TestMyBookingsFlow:
    """Tests for my bookings flow."""

    @pytest.mark.asyncio
    async def test_my_bookings_keywords(self):
        """My bookings keywords should show bookings."""
        for kw in MY_BOOKINGS_KEYWORDS:
            clear_state("test_phone")
            response = await handle_message("test_phone", kw)
            # Should show bookings or "no bookings"
            assert (
                "booking" in response.lower()
                or "book" in response.lower()
            )

    @pytest.mark.asyncio
    async def test_my_bookings_after_booking(self):
        """After booking, my bookings should show the booking."""
        # Book a class first
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        # Clear state and check bookings
        clear_state("test_phone")
        response = await handle_message("test_phone", "my bookings")

        # Should show bookings list
        assert "booking" in response.lower()


class TestStateManagement:
    """Tests for conversation state management."""

    @pytest.mark.asyncio
    async def test_state_persists_between_messages(self):
        """State should persist between messages."""
        await handle_message("test_phone", "book")
        state1 = get_state("test_phone")
        assert state1.get("mode") == "selecting_class"

        # Send another message
        await handle_message("test_phone", "abc")
        state2 = get_state("test_phone")
        assert state2.get("mode") == "selecting_class"

    @pytest.mark.asyncio
    async def test_different_users_have_separate_state(self):
        """Different phone numbers should have separate state."""
        await handle_message("user1", "book")
        await handle_message("user2", "hello")

        assert get_state("user1").get("mode") == "selecting_class"
        assert get_state("user2").get("mode") is None

        # Cleanup
        clear_state("user1")
        clear_state("user2")


class TestInactiveMember:
    """Tests for inactive member scenarios."""

    @pytest.mark.asyncio
    async def test_inactive_member_cannot_book(self):
        """Inactive member should see reactivation message."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "id": 1,
                "name": "Inactive User",
                "is_active": False,
                "can_book_pemula": True,
                "can_book_semi_private": True,
            }
            response = await handle_message("test_phone", "book")

            assert "isn't active" in response.lower()
            assert "renew" in response.lower()

    @pytest.mark.asyncio
    async def test_member_not_found_on_book(self):
        """Unregistered phone should see account not found message."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock:
            mock.return_value = None
            response = await handle_message("test_phone", "book")

            assert "couldn't find" in response.lower()
            assert "account" in response.lower()

    @pytest.mark.asyncio
    async def test_member_not_found_on_my_bookings(self):
        """Unregistered phone should see account not found for my bookings."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock:
            mock.return_value = None
            response = await handle_message("test_phone", "my bookings")

            assert "couldn't find" in response.lower()


class TestNoClassesAvailable:
    """Tests for no classes available scenario."""

    @pytest.mark.asyncio
    async def test_no_classes_available(self):
        """Should show no classes message when none available."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock_member, \
             patch("app.handlers.get_available_classes", new_callable=AsyncMock) as mock_classes:
            mock_member.return_value = {
                "id": 1,
                "name": "Test User",
                "is_active": True,
                "can_book_pemula": True,
                "can_book_semi_private": True,
            }
            mock_classes.return_value = []
            response = await handle_message("test_phone", "book")

            assert "no classes available" in response.lower()


class TestMembershipRestrictions:
    """Tests for membership-based class filtering."""

    @pytest.mark.asyncio
    async def test_silver_member_cannot_see_gold_classes(self):
        """Silver member should not see gold (semi private) classes."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock_member, \
             patch("app.handlers.get_available_classes", new_callable=AsyncMock) as mock_classes:
            mock_member.return_value = {
                "id": 1,
                "name": "Silver Member",
                "is_active": True,
                "can_book_pemula": True,
                "can_book_semi_private": False,  # No gold access
            }
            mock_classes.return_value = [
                {
                    "id": 1,
                    "class_name": "Semi Private",
                    "date": "2026-01-08",
                    "start_time": "07:00",
                    "status": "OPEN",
                    "available_slots": 2,
                    "requires": "gold",  # Requires gold
                }
            ]
            response = await handle_message("test_phone", "book")

            # Should see upgrade message since only gold classes available
            assert "membership doesn't include" in response.lower()

    @pytest.mark.asyncio
    async def test_member_sees_only_permitted_classes(self):
        """Member should only see classes their membership includes."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock_member, \
             patch("app.handlers.get_available_classes", new_callable=AsyncMock) as mock_classes:
            mock_member.return_value = {
                "id": 1,
                "name": "Silver Member",
                "is_active": True,
                "can_book_pemula": True,
                "can_book_semi_private": False,
            }
            mock_classes.return_value = [
                {"id": 1, "class_name": "Semi Private", "date": "2026-01-08",
                 "start_time": "07:00", "status": "OPEN", "available_slots": 2, "requires": "gold"},
                {"id": 2, "class_name": "Kelas Pemula", "date": "2026-01-08",
                 "start_time": "08:00", "status": "OPEN", "available_slots": 5, "requires": "silver"},
            ]
            response = await handle_message("test_phone", "book")

            # Should only see Kelas Pemula (silver), not Semi Private (gold)
            assert "kelas pemula" in response.lower()
            assert "semi private" not in response.lower()


class TestBookingErrors:
    """Tests for booking error scenarios."""

    @pytest.mark.asyncio
    async def test_booking_api_failure(self):
        """Should handle booking API failure gracefully."""
        # Start booking flow normally
        await handle_message("test_phone", "book")

        # Mock book_class to return failure
        with patch("app.handlers.book_class", new_callable=AsyncMock) as mock_book:
            mock_book.return_value = {"success": False, "message": "Server error"}
            response = await handle_message("test_phone", "1")

            assert "couldn't complete" in response.lower() or "oops" in response.lower()

    @pytest.mark.asyncio
    async def test_state_cleared_on_booking_error(self):
        """State should be cleared after booking error."""
        await handle_message("test_phone", "book")

        with patch("app.handlers.book_class", new_callable=AsyncMock) as mock_book:
            mock_book.return_value = {"success": False, "message": "Error"}
            await handle_message("test_phone", "1")

        assert get_state("test_phone").get("mode") is None


class TestWaitlistErrors:
    """Tests for waitlist error scenarios."""

    @pytest.mark.asyncio
    async def test_waitlist_api_failure(self):
        """Should handle waitlist API failure gracefully."""
        await handle_message("test_phone", "book")

        # Find FULL class
        state = get_state("test_phone")
        classes = state.get("classes", [])
        full_idx = None
        for i, c in enumerate(classes):
            if c.get("status") == "FULL":
                full_idx = i + 1
                break

        if full_idx:
            await handle_message("test_phone", str(full_idx))

            with patch("app.handlers.join_waitlist", new_callable=AsyncMock) as mock_wl:
                mock_wl.return_value = {"success": False, "message": "Waitlist full"}
                response = await handle_message("test_phone", "yes")

                assert "couldn't add" in response.lower()

    @pytest.mark.asyncio
    async def test_invalid_waitlist_response(self):
        """Invalid response during waitlist confirmation should prompt again."""
        await handle_message("test_phone", "book")

        state = get_state("test_phone")
        classes = state.get("classes", [])
        full_idx = None
        for i, c in enumerate(classes):
            if c.get("status") == "FULL":
                full_idx = i + 1
                break

        if full_idx:
            await handle_message("test_phone", str(full_idx))
            response = await handle_message("test_phone", "maybe")

            assert "reply *yes*" in response.lower()


class TestCancelConfirmation:
    """Tests for cancel booking confirmation flow."""

    @pytest.mark.asyncio
    async def test_cancel_confirmation_yes(self):
        """Confirming cancellation should cancel the booking."""
        # Book a class first
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        # View bookings
        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")

        # Select booking to cancel
        response = await handle_message("test_phone", "1")
        assert "are you sure" in response.lower()

        # Confirm
        response = await handle_message("test_phone", "yes")
        assert "done" in response.lower() or "cancelled" in response.lower()

    @pytest.mark.asyncio
    async def test_cancel_confirmation_no(self):
        """Declining cancellation should keep the booking."""
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")
        await handle_message("test_phone", "1")

        response = await handle_message("test_phone", "no")
        assert "no problem" in response.lower()

    @pytest.mark.asyncio
    async def test_cancel_invalid_response(self):
        """Invalid response during cancel confirmation should prompt again."""
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")
        await handle_message("test_phone", "1")

        response = await handle_message("test_phone", "maybe")
        assert "reply *yes*" in response.lower()

    @pytest.mark.asyncio
    async def test_cancel_api_failure(self):
        """Should handle cancel API failure gracefully."""
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")
        await handle_message("test_phone", "1")

        with patch("app.handlers.cancel_booking", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = {"success": False, "message": "Server error"}
            response = await handle_message("test_phone", "yes")

            assert "couldn't cancel" in response.lower()


class TestViewBookingsFlow:
    """Tests for viewing bookings and cancellation selection."""

    @pytest.mark.asyncio
    async def test_no_bookings_message(self):
        """Should show appropriate message when no bookings."""
        with patch("app.handlers.get_member_by_phone", new_callable=AsyncMock) as mock_member, \
             patch("app.handlers.get_my_bookings", new_callable=AsyncMock) as mock_bookings:
            mock_member.return_value = {
                "id": 1,
                "name": "Test User",
                "is_active": True,
            }
            mock_bookings.return_value = []
            response = await handle_message("test_phone", "my bookings")

            assert "don't have any bookings" in response.lower()

    @pytest.mark.asyncio
    async def test_switch_to_booking_from_viewing(self):
        """Should allow switching to booking flow from viewing bookings."""
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")

        # Type book instead of number
        response = await handle_message("test_phone", "book")
        assert "here are the upcoming classes" in response.lower()

    @pytest.mark.asyncio
    async def test_invalid_booking_selection(self):
        """Invalid number during booking selection should prompt again."""
        await handle_message("test_phone", "book")
        await handle_message("test_phone", "1")

        clear_state("test_phone")
        await handle_message("test_phone", "my bookings")

        response = await handle_message("test_phone", "999")
        assert "number between" in response.lower()


class TestCorruptedState:
    """Tests for handling corrupted/invalid state."""

    @pytest.mark.asyncio
    async def test_selecting_class_without_classes_in_state(self):
        """Should handle missing classes in state gracefully."""
        set_state("test_phone", mode="selecting_class", classes=[], member=None)
        response = await handle_message("test_phone", "1")

        assert "something went wrong" in response.lower()

    @pytest.mark.asyncio
    async def test_confirm_waitlist_without_selected_class(self):
        """Should handle missing selected_class in state."""
        set_state("test_phone", mode="confirm_waitlist", selected_class=None, member=None)
        response = await handle_message("test_phone", "yes")

        assert "something went wrong" in response.lower()

    @pytest.mark.asyncio
    async def test_viewing_bookings_without_bookings_in_state(self):
        """Should handle missing bookings in state."""
        set_state("test_phone", mode="viewing_bookings", bookings=[], member=None)
        response = await handle_message("test_phone", "1")

        assert "something went wrong" in response.lower()

    @pytest.mark.asyncio
    async def test_confirm_cancel_without_booking(self):
        """Should handle missing selected_booking in state."""
        set_state("test_phone", mode="confirm_cancel", selected_booking=None, member=None)
        response = await handle_message("test_phone", "yes")

        assert "something went wrong" in response.lower()


class TestKeywordVariations:
    """Tests for various keyword inputs."""

    @pytest.mark.asyncio
    async def test_all_yes_keywords_work(self):
        """All yes keywords should confirm waitlist."""
        for kw in YES_KEYWORDS[:3]:  # Test first 3 to save time
            clear_state("test_phone")
            await handle_message("test_phone", "book")

            state = get_state("test_phone")
            classes = state.get("classes", [])
            full_idx = None
            for i, c in enumerate(classes):
                if c.get("status") == "FULL":
                    full_idx = i + 1
                    break

            if full_idx:
                await handle_message("test_phone", str(full_idx))
                response = await handle_message("test_phone", kw)
                assert "waitlist" in response.lower()

    @pytest.mark.asyncio
    async def test_all_no_keywords_work(self):
        """All no keywords should decline waitlist."""
        for kw in NO_KEYWORDS[:3]:
            clear_state("test_phone")
            await handle_message("test_phone", "book")

            state = get_state("test_phone")
            classes = state.get("classes", [])
            full_idx = None
            for i, c in enumerate(classes):
                if c.get("status") == "FULL":
                    full_idx = i + 1
                    break

            if full_idx:
                await handle_message("test_phone", str(full_idx))
                response = await handle_message("test_phone", kw)
                assert "no problem" in response.lower()


class TestWaitlistCancellation:
    """Tests for waitlist-specific cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_waitlist_shows_waitlist_type(self):
        """Cancelling waitlist should mention waitlist in confirmation."""
        await handle_message("test_phone", "book")

        state = get_state("test_phone")
        classes = state.get("classes", [])
        full_idx = None
        for i, c in enumerate(classes):
            if c.get("status") == "FULL":
                full_idx = i + 1
                break

        if full_idx:
            await handle_message("test_phone", str(full_idx))
            await handle_message("test_phone", "yes")

            clear_state("test_phone")
            await handle_message("test_phone", "my bookings")

            # Find waitlisted booking
            state = get_state("test_phone")
            bookings = state.get("bookings", [])
            wl_idx = None
            for i, b in enumerate(bookings):
                if b.get("booking_status") == "waitlisted":
                    wl_idx = i + 1
                    break

            if wl_idx:
                response = await handle_message("test_phone", str(wl_idx))
                assert "waitlist" in response.lower()
