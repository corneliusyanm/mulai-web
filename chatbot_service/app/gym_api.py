"""
Client for Mulai Gym API.
Switches between mock data and real API based on configuration.
"""

import httpx

from app.config import get_settings
from app.mock_data import (
    get_member_bookings,
    get_mock_classes,
    get_mock_member,
    mock_book_class,
    mock_cancel_booking,
    mock_join_waitlist,
)

HTTP_TIMEOUT = 30


async def get_available_classes() -> list[dict]:
    """
    Get upcoming bookable class instances.

    Returns:
        List of class dicts with id, class_name, date, start_time,
        status, available_slots, max_members, requires.
    """
    settings = get_settings()

    if settings.use_mock_data:
        return get_mock_classes()

    url = f"{settings.gym_api_base_url}/api/chatbot/classes/"
    headers = {"X-API-Key": settings.gym_api_key}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_member_by_phone(phone: str) -> dict | None:
    """
    Look up a member by phone number.

    Args:
        phone: Phone number in format 628xxx (no + prefix)

    Returns:
        Member info dict or None if not found.
    """
    settings = get_settings()

    if settings.use_mock_data:
        return get_mock_member(phone)

    url = f"{settings.gym_api_base_url}/api/chatbot/member/"
    headers = {"X-API-Key": settings.gym_api_key}
    params = {"phone": phone}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


async def book_class(member_id: int, class_instance_id: int) -> dict:
    """
    Book a class for a member.

    Args:
        member_id: Member's database ID
        class_instance_id: Class instance to book

    Returns:
        Dict with 'success' bool and 'message' str.
    """
    settings = get_settings()

    if settings.use_mock_data:
        return mock_book_class(member_id, class_instance_id)

    url = f"{settings.gym_api_base_url}/api/chatbot/book/"
    headers = {"X-API-Key": settings.gym_api_key}
    payload = {"member_id": member_id, "class_instance_id": class_instance_id}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()


async def join_waitlist(member_id: int, class_instance_id: int) -> dict:
    """
    Add member to class waitlist.

    Args:
        member_id: Member's database ID
        class_instance_id: Class instance to join waitlist

    Returns:
        Dict with 'success' bool and 'message' str.
    """
    settings = get_settings()

    if settings.use_mock_data:
        return mock_join_waitlist(member_id, class_instance_id)

    url = f"{settings.gym_api_base_url}/api/chatbot/waitlist/"
    headers = {"X-API-Key": settings.gym_api_key}
    payload = {"member_id": member_id, "class_instance_id": class_instance_id}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()


async def cancel_booking(member_id: int, class_instance_id: int) -> dict:
    """
    Cancel a class booking or leave waitlist.

    Args:
        member_id: Member's database ID
        class_instance_id: Class instance to cancel

    Returns:
        Dict with 'success' bool and 'message' str.
    """
    settings = get_settings()

    if settings.use_mock_data:
        return mock_cancel_booking(member_id, class_instance_id)

    url = f"{settings.gym_api_base_url}/api/chatbot/cancel/"
    headers = {"X-API-Key": settings.gym_api_key}
    payload = {"member_id": member_id, "class_instance_id": class_instance_id}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()


async def get_my_bookings(member_id: int) -> list[dict]:
    """
    Get member's current bookings and waitlist entries.

    Args:
        member_id: Member's database ID

    Returns:
        List of booking dicts with 'booking_status' field ('booked' or 'waitlisted').
    """
    settings = get_settings()

    if settings.use_mock_data:
        return get_member_bookings(member_id)

    url = f"{settings.gym_api_base_url}/api/chatbot/my-bookings/"
    headers = {"X-API-Key": settings.gym_api_key}
    params = {"member_id": member_id}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
