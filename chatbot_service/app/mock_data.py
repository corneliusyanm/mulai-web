"""
Mock data for local testing without connecting to mulaigym.id.
Based on real production data from Mulai Gym.

This module maintains in-memory state so bookings persist during the session.
"""

from datetime import date, time, timedelta
from typing import TypedDict


class ClassInstance(TypedDict):
    id: int
    class_name: str
    date: str
    start_time: str
    end_time: str
    status: str
    available_slots: int
    max_members: int
    requires: str
    booked_members: list[int]
    waitlisted_members: list[int]


# Class types available at Mulai Gym
CLASSES = {
    1: {"name": "Kelas Pemula (Push)", "max_members": 6, "requires": "silver"},
    2: {"name": "Semi Private", "max_members": 4, "requires": "gold"},
    3: {"name": "Kelas Pemula (Pull)", "max_members": 6, "requires": "silver"},
    4: {"name": "Kelas Pemula (Leg & Core)", "max_members": 6, "requires": "silver"},
}

# In-memory storage - persists during server lifetime
_mock_classes: list[ClassInstance] = []
_last_generated_date: date | None = None


def _generate_classes() -> list[ClassInstance]:
    """Generate mock class instances for the next 3 days."""
    today = date.today()
    classes: list[ClassInstance] = []

    for day_offset in range(3):
        target_date = today + timedelta(days=day_offset)
        day_of_week = target_date.weekday()

        # Semi Private classes (every day)
        semi_private_times = [
            (time(7, 0), time(8, 0)),
            (time(9, 0), time(10, 0)),
            (time(16, 15), time(17, 15)),
            (time(19, 0), time(20, 0)),
        ]
        for idx, (start, end) in enumerate(semi_private_times):
            # 16:15 slot (idx=2) is FULL, others have 2 spots left
            is_full_slot = idx == 2
            initial_booked = 4 if is_full_slot else 2
            classes.append(
                {
                    "id": 1000 + day_offset * 20 + idx,
                    "class_name": "Semi Private",
                    "date": target_date.isoformat(),
                    "start_time": start.strftime("%H:%M"),
                    "end_time": end.strftime("%H:%M"),
                    "status": "FULL" if is_full_slot else "OPEN",
                    "available_slots": 4 - initial_booked,
                    "max_members": 4,
                    "requires": "gold",
                    "booked_members": list(range(100, 100 + initial_booked)),
                    "waitlisted_members": [50, 51] if is_full_slot else [],
                }
            )

        # Kelas Pemula based on day of week
        pemula_schedule = {
            0: [1],  # Monday: Push
            1: [3],  # Tuesday: Pull
            2: [4],  # Wednesday: Leg & Core
            3: [1],  # Thursday: Push
            4: [3],  # Friday: Pull
            5: [4],  # Saturday: Leg & Core
            6: [],  # Sunday: No classes
        }

        pemula_times = [
            (time(8, 0), time(8, 45)),
            (time(15, 30), time(16, 15)),
            (time(17, 15), time(18, 0)),
            (time(18, 15), time(19, 0)),
        ]

        for class_id in pemula_schedule.get(day_of_week, []):
            class_info = CLASSES[class_id]
            for idx, (start, end) in enumerate(pemula_times):
                # Pemula classes have plenty of room (no "X spots left" shown)
                initial_booked = 0
                classes.append(
                    {
                        "id": 2000 + day_offset * 20 + class_id * 10 + idx,
                        "class_name": class_info["name"],
                        "date": target_date.isoformat(),
                        "start_time": start.strftime("%H:%M"),
                        "end_time": end.strftime("%H:%M"),
                        "status": "OPEN",
                        "available_slots": class_info["max_members"] - initial_booked,
                        "max_members": class_info["max_members"],
                        "requires": class_info["requires"],
                        "booked_members": [],
                        "waitlisted_members": [],
                    }
                )

    return classes


def _ensure_classes_generated():
    """Ensure classes are generated, regenerate if date changed."""
    global _mock_classes, _last_generated_date

    today = date.today()
    if _last_generated_date != today or not _mock_classes:
        _mock_classes = _generate_classes()
        _last_generated_date = today


def get_mock_classes() -> list[dict]:
    """
    Get mock upcoming class instances.
    Returns classes in a format similar to the real API.
    """
    _ensure_classes_generated()

    # Return a copy without internal tracking fields
    return [
        {
            "id": c["id"],
            "class_name": c["class_name"],
            "date": c["date"],
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "status": c["status"],
            "available_slots": c["available_slots"],
            "max_members": c["max_members"],
            "requires": c["requires"],
        }
        for c in _mock_classes
    ]


def _find_class(class_instance_id: int) -> ClassInstance | None:
    """Find a class by ID."""
    _ensure_classes_generated()
    for c in _mock_classes:
        if c["id"] == class_instance_id:
            return c
    return None


def _update_class_status(c: ClassInstance):
    """Update class status based on bookings."""
    c["available_slots"] = c["max_members"] - len(c["booked_members"])
    if c["available_slots"] <= 0:
        c["status"] = "FULL"
        c["available_slots"] = 0
    else:
        c["status"] = "OPEN"


def get_mock_member(phone: str) -> dict | None:
    """
    Return a mock member for testing.
    Accepts any phone number and returns a test user.
    """
    if not phone:
        return None

    return {
        "id": 1,
        "name": "Test Member",
        "phone_number": phone,
        "is_active": True,
        "can_book_pemula": True,
        "can_book_semi_private": True,
    }


def mock_book_class(member_id: int, class_instance_id: int) -> dict:
    """
    Book a class. Actually updates the in-memory state.
    """
    c = _find_class(class_instance_id)

    if not c:
        return {"success": False, "message": "Class not found"}

    if member_id in c["booked_members"]:
        return {"success": False, "message": "You've already booked this class"}

    if c["status"] == "FULL":
        return {"success": False, "message": "Class is full"}

    # Remove from waitlist if present
    if member_id in c["waitlisted_members"]:
        c["waitlisted_members"].remove(member_id)

    c["booked_members"].append(member_id)
    _update_class_status(c)

    return {
        "success": True,
        "message": "Booking confirmed",
        "booking_id": 12345,
    }


def mock_join_waitlist(member_id: int, class_instance_id: int) -> dict:
    """
    Join waitlist. Actually updates the in-memory state.
    """
    c = _find_class(class_instance_id)

    if not c:
        return {"success": False, "message": "Class not found"}

    if member_id in c["booked_members"]:
        return {"success": False, "message": "You're already booked for this class"}

    if member_id in c["waitlisted_members"]:
        return {"success": False, "message": "You're already on the waitlist"}

    c["waitlisted_members"].append(member_id)

    return {"success": True, "message": "Added to waitlist"}


def mock_cancel_booking(member_id: int, class_instance_id: int) -> dict:
    """
    Cancel a booking. Updates in-memory state and moves waitlist if applicable.
    """
    c = _find_class(class_instance_id)

    if not c:
        return {"success": False, "message": "Class not found"}

    if member_id not in c["booked_members"]:
        # Check waitlist
        if member_id in c["waitlisted_members"]:
            c["waitlisted_members"].remove(member_id)
            return {"success": True, "message": "Removed from waitlist"}
        return {"success": False, "message": "You don't have a booking for this class"}

    c["booked_members"].remove(member_id)
    _update_class_status(c)

    # Move first waitlisted member to booked
    if c["waitlisted_members"] and c["available_slots"] > 0:
        next_member = c["waitlisted_members"].pop(0)
        c["booked_members"].append(next_member)
        _update_class_status(c)

    return {"success": True, "message": "Booking cancelled"}


def get_member_bookings(member_id: int) -> list[dict]:
    """Get all bookings and waitlist entries for a member."""
    _ensure_classes_generated()

    bookings = []
    for c in _mock_classes:
        if member_id in c["booked_members"]:
            bookings.append({**c, "booking_status": "booked"})
        elif member_id in c["waitlisted_members"]:
            bookings.append({**c, "booking_status": "waitlisted"})

    return bookings
