"""
Unit tests for mock data module.
Tests booking, cancellation, and waitlist logic.
"""

import pytest

from app.mock_data import (
    get_member_bookings,
    get_mock_classes,
    get_mock_member,
    mock_book_class,
    mock_cancel_booking,
    mock_join_waitlist,
    _mock_classes,
    _find_class,
)


class TestGetMockClasses:
    """Tests for get_mock_classes function."""

    def test_returns_list(self):
        """Should return a list of classes."""
        classes = get_mock_classes()
        assert isinstance(classes, list)
        assert len(classes) > 0

    def test_class_has_required_fields(self):
        """Each class should have required fields."""
        classes = get_mock_classes()
        required_fields = [
            "id", "class_name", "date", "start_time", "end_time",
            "status", "available_slots", "max_members", "requires"
        ]

        for c in classes:
            for field in required_fields:
                assert field in c, f"Missing field: {field}"

    def test_has_full_and_open_classes(self):
        """Should have both FULL and OPEN classes for testing."""
        classes = get_mock_classes()
        statuses = {c["status"] for c in classes}
        assert "OPEN" in statuses
        assert "FULL" in statuses


class TestGetMockMember:
    """Tests for get_mock_member function."""

    def test_returns_member_for_any_phone(self):
        """Should return a member for any phone number."""
        member = get_mock_member("6281234567890")
        assert member is not None
        assert member["name"] == "Test Member"

    def test_returns_none_for_empty_phone(self):
        """Should return None for empty phone number."""
        member = get_mock_member("")
        assert member is None

    def test_member_has_required_fields(self):
        """Member should have required fields."""
        member = get_mock_member("6281234567890")
        assert "id" in member
        assert "name" in member
        assert "is_active" in member
        assert "can_book_pemula" in member
        assert "can_book_semi_private" in member


class TestMockBookClass:
    """Tests for mock_book_class function."""

    def test_book_open_class(self):
        """Should successfully book an open class."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        result = mock_book_class(999, open_class["id"])
        assert result["success"] is True

    def test_book_full_class_fails(self):
        """Should fail to book a full class."""
        classes = get_mock_classes()
        full_class = next(c for c in classes if c["status"] == "FULL")

        result = mock_book_class(888, full_class["id"])
        assert result["success"] is False
        assert "full" in result["message"].lower()

    def test_double_booking_fails(self):
        """Should fail when trying to book same class twice."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        mock_book_class(777, open_class["id"])
        result = mock_book_class(777, open_class["id"])

        assert result["success"] is False
        assert "already" in result["message"].lower()

    def test_booking_nonexistent_class_fails(self):
        """Should fail for nonexistent class."""
        result = mock_book_class(1, 99999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestMockJoinWaitlist:
    """Tests for mock_join_waitlist function."""

    def test_join_waitlist(self):
        """Should successfully join waitlist."""
        classes = get_mock_classes()
        any_class = classes[0]

        result = mock_join_waitlist(666, any_class["id"])
        assert result["success"] is True

    def test_double_waitlist_fails(self):
        """Should fail when already on waitlist."""
        classes = get_mock_classes()
        any_class = classes[0]

        mock_join_waitlist(555, any_class["id"])
        result = mock_join_waitlist(555, any_class["id"])

        assert result["success"] is False
        assert "already" in result["message"].lower()

    def test_waitlist_when_booked_fails(self):
        """Should fail when already booked."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        mock_book_class(444, open_class["id"])
        result = mock_join_waitlist(444, open_class["id"])

        assert result["success"] is False


class TestMockCancelBooking:
    """Tests for mock_cancel_booking function."""

    def test_cancel_booking(self):
        """Should successfully cancel a booking."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        mock_book_class(333, open_class["id"])
        result = mock_cancel_booking(333, open_class["id"])

        assert result["success"] is True
        assert "cancelled" in result["message"].lower()

    def test_cancel_waitlist(self):
        """Should successfully leave waitlist."""
        classes = get_mock_classes()
        any_class = classes[0]

        mock_join_waitlist(222, any_class["id"])
        result = mock_cancel_booking(222, any_class["id"])

        assert result["success"] is True
        assert "waitlist" in result["message"].lower()

    def test_cancel_no_booking_fails(self):
        """Should fail when no booking exists."""
        classes = get_mock_classes()
        result = mock_cancel_booking(111, classes[0]["id"])

        assert result["success"] is False


class TestGetMemberBookings:
    """Tests for get_member_bookings function."""

    def test_returns_empty_for_no_bookings(self):
        """Should return empty list for member with no bookings."""
        bookings = get_member_bookings(99999)
        assert isinstance(bookings, list)

    def test_returns_booked_classes(self):
        """Should return booked classes."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        mock_book_class(12345, open_class["id"])
        bookings = get_member_bookings(12345)

        assert len(bookings) > 0
        assert any(b["booking_status"] == "booked" for b in bookings)

    def test_returns_waitlisted_classes(self):
        """Should return waitlisted classes."""
        classes = get_mock_classes()
        any_class = classes[0]

        mock_join_waitlist(12346, any_class["id"])
        bookings = get_member_bookings(12346)

        assert len(bookings) > 0
        assert any(b["booking_status"] == "waitlisted" for b in bookings)


class TestAvailableSlotsTracking:
    """Tests for available slots tracking."""

    def test_booking_decreases_available_slots(self):
        """Booking should decrease available slots."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN" and c["available_slots"] > 1)

        initial_slots = open_class["available_slots"]
        mock_book_class(54321, open_class["id"])

        # Refresh classes list
        updated_classes = get_mock_classes()
        updated_class = next(c for c in updated_classes if c["id"] == open_class["id"])

        assert updated_class["available_slots"] == initial_slots - 1

    def test_cancellation_increases_available_slots(self):
        """Cancellation should increase available slots."""
        classes = get_mock_classes()
        open_class = next(c for c in classes if c["status"] == "OPEN")

        mock_book_class(65432, open_class["id"])

        # Get slots after booking
        classes = get_mock_classes()
        booked_class = next(c for c in classes if c["id"] == open_class["id"])
        slots_after_booking = booked_class["available_slots"]

        # Cancel
        mock_cancel_booking(65432, open_class["id"])

        # Check slots after cancellation
        classes = get_mock_classes()
        cancelled_class = next(c for c in classes if c["id"] == open_class["id"])

        assert cancelled_class["available_slots"] == slots_after_booking + 1
