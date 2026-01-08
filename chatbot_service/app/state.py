"""
Simple in-memory conversation state management.
For production, consider using Redis or a database.
"""
from datetime import datetime, timedelta
from typing import TypedDict


class ConversationState(TypedDict, total=False):
    mode: str  # "idle", "selecting_class", "confirm_waitlist"
    classes: list[dict]  # Available classes shown to user
    selected_class: dict | None  # Class user selected (for waitlist confirmation)
    member: dict | None  # Member info
    expires: datetime  # When this state expires


# In-memory state storage (phone -> state)
_state: dict[str, ConversationState] = {}

# State expires after 10 minutes of inactivity
STATE_TTL_MINUTES = 10


def get_state(phone: str) -> ConversationState:
    """Get conversation state for a phone number."""
    state = _state.get(phone, {})

    # Check if expired
    if state.get("expires") and datetime.now() > state["expires"]:
        clear_state(phone)
        return {}

    return state


def set_state(phone: str, **kwargs) -> None:
    """Update conversation state for a phone number."""
    current = _state.get(phone, {})
    current.update(kwargs)
    current["expires"] = datetime.now() + timedelta(minutes=STATE_TTL_MINUTES)
    _state[phone] = current


def clear_state(phone: str) -> None:
    """Clear conversation state for a phone number."""
    _state.pop(phone, None)


