"""
Unit tests for state management module.
Tests state operations and expiration logic.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.state import (
    get_state,
    set_state,
    clear_state,
    STATE_TTL_MINUTES,
    _state,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Clean state before and after each test."""
    _state.clear()
    yield
    _state.clear()


class TestGetState:
    """Tests for get_state function."""

    def test_returns_empty_dict_for_new_phone(self):
        """Should return empty dict for unknown phone."""
        state = get_state("unknown_phone")
        assert state == {}

    def test_returns_stored_state(self):
        """Should return previously stored state."""
        set_state("test_phone", mode="test", value=123)
        state = get_state("test_phone")

        assert state["mode"] == "test"
        assert state["value"] == 123

    def test_returns_empty_for_expired_state(self):
        """Should return empty dict for expired state."""
        # Set state with expired timestamp
        _state["test_phone"] = {
            "mode": "test",
            "expires": datetime.now() - timedelta(minutes=1)
        }

        state = get_state("test_phone")
        assert state == {}

    def test_returns_valid_unexpired_state(self):
        """Should return state that hasn't expired."""
        future_time = datetime.now() + timedelta(minutes=5)
        _state["test_phone"] = {"mode": "test", "expires": future_time}

        state = get_state("test_phone")
        assert state["mode"] == "test"

    def test_clears_state_on_expiration(self):
        """Should clear state from memory when expired."""
        _state["test_phone"] = {
            "mode": "test",
            "expires": datetime.now() - timedelta(minutes=1)
        }

        get_state("test_phone")

        # State should be removed from memory
        assert "test_phone" not in _state


class TestSetState:
    """Tests for set_state function."""

    def test_creates_new_state(self):
        """Should create state for new phone."""
        set_state("test_phone", mode="booking")

        assert "test_phone" in _state
        assert _state["test_phone"]["mode"] == "booking"

    def test_updates_existing_state(self):
        """Should update existing state."""
        set_state("test_phone", mode="booking")
        set_state("test_phone", mode="waitlist", step=2)

        assert _state["test_phone"]["mode"] == "waitlist"
        assert _state["test_phone"]["step"] == 2

    def test_preserves_other_fields_on_update(self):
        """Should preserve fields not being updated."""
        set_state("test_phone", mode="booking", member_id=1)
        set_state("test_phone", step=2)

        assert _state["test_phone"]["mode"] == "booking"
        assert _state["test_phone"]["member_id"] == 1
        assert _state["test_phone"]["step"] == 2

    def test_sets_expiration_time(self):
        """Should set expiration time."""
        before = datetime.now()
        set_state("test_phone", mode="test")
        after = datetime.now()

        expires = _state["test_phone"]["expires"]
        expected_min = before + timedelta(minutes=STATE_TTL_MINUTES)
        expected_max = after + timedelta(minutes=STATE_TTL_MINUTES)

        assert expected_min <= expires <= expected_max

    def test_resets_expiration_on_update(self):
        """Should reset expiration on each update."""
        set_state("test_phone", mode="test")
        old_expires = _state["test_phone"]["expires"]

        # Wait a tiny bit and update
        set_state("test_phone", step=2)
        new_expires = _state["test_phone"]["expires"]

        # New expiration should be >= old
        assert new_expires >= old_expires

    def test_accepts_complex_values(self):
        """Should accept complex data types."""
        classes = [{"id": 1, "name": "Test"}]
        member = {"id": 1, "name": "John"}

        set_state("test_phone", classes=classes, member=member)

        assert _state["test_phone"]["classes"] == classes
        assert _state["test_phone"]["member"] == member


class TestClearState:
    """Tests for clear_state function."""

    def test_removes_state(self):
        """Should remove state for phone."""
        set_state("test_phone", mode="test")
        clear_state("test_phone")

        assert "test_phone" not in _state

    def test_handles_nonexistent_phone(self):
        """Should not raise for nonexistent phone."""
        # Should not raise
        clear_state("unknown_phone")

    def test_only_clears_specified_phone(self):
        """Should only clear state for specified phone."""
        set_state("phone1", mode="test1")
        set_state("phone2", mode="test2")

        clear_state("phone1")

        assert "phone1" not in _state
        assert "phone2" in _state


class TestStateIsolation:
    """Tests for state isolation between users."""

    def test_different_phones_have_separate_state(self):
        """Each phone should have independent state."""
        set_state("phone1", mode="mode1", value=1)
        set_state("phone2", mode="mode2", value=2)

        state1 = get_state("phone1")
        state2 = get_state("phone2")

        assert state1["mode"] == "mode1"
        assert state1["value"] == 1
        assert state2["mode"] == "mode2"
        assert state2["value"] == 2

    def test_clearing_one_doesnt_affect_others(self):
        """Clearing one phone shouldn't affect others."""
        set_state("phone1", mode="test")
        set_state("phone2", mode="test")

        clear_state("phone1")

        assert "phone1" not in _state
        assert get_state("phone2")["mode"] == "test"

    def test_updating_one_doesnt_affect_others(self):
        """Updating one phone shouldn't affect others."""
        set_state("phone1", mode="original")
        set_state("phone2", mode="original")

        set_state("phone1", mode="updated")

        assert get_state("phone1")["mode"] == "updated"
        assert get_state("phone2")["mode"] == "original"


class TestStateTTL:
    """Tests for state TTL configuration."""

    def test_ttl_is_positive(self):
        """TTL should be a positive number."""
        assert STATE_TTL_MINUTES > 0

    def test_ttl_is_reasonable(self):
        """TTL should be between 1 and 60 minutes."""
        assert 1 <= STATE_TTL_MINUTES <= 60

    def test_state_valid_within_ttl(self):
        """State should be valid within TTL period."""
        with patch("app.state.datetime") as mock_dt:
            # Set initial time
            base_time = datetime(2026, 1, 8, 12, 0, 0)
            mock_dt.now.return_value = base_time
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            set_state("test_phone", mode="test")

            # Move time forward but within TTL
            mock_dt.now.return_value = base_time + timedelta(minutes=STATE_TTL_MINUTES - 1)

            state = get_state("test_phone")
            assert state.get("mode") == "test"


class TestStateEdgeCases:
    """Tests for edge cases in state management."""

    def test_empty_phone_number(self):
        """Should handle empty phone number."""
        set_state("", mode="test")
        state = get_state("")

        assert state.get("mode") == "test"
        clear_state("")

    def test_special_characters_in_phone(self):
        """Should handle special characters in phone."""
        phone = "+62-812-345-6789"
        set_state(phone, mode="test")

        state = get_state(phone)
        assert state.get("mode") == "test"

    def test_none_values_in_state(self):
        """Should handle None values in state."""
        set_state("test_phone", mode=None, member=None)

        state = get_state("test_phone")
        assert state.get("mode") is None
        assert state.get("member") is None

    def test_overwrite_with_none(self):
        """Should allow overwriting value with None."""
        set_state("test_phone", mode="test", member={"id": 1})
        set_state("test_phone", member=None)

        state = get_state("test_phone")
        assert state.get("mode") == "test"
        assert state.get("member") is None

    def test_large_state_data(self):
        """Should handle large data in state."""
        large_classes = [{"id": i, "name": f"Class {i}"} for i in range(100)]
        set_state("test_phone", classes=large_classes)

        state = get_state("test_phone")
        assert len(state.get("classes", [])) == 100
