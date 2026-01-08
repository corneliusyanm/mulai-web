"""
API endpoints for the WhatsApp chatbot.
These endpoints are called by the FastAPI chatbot service.
"""
import json
from datetime import datetime
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from django.conf import settings

from accounts.models import Member
from classes.models import ClassInstance


def api_key_required(view_func):
    """Decorator to require API key for write operations."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        expected_key = getattr(settings, "CHATBOT_API_KEY", "")

        if not expected_key:
            # If no key configured, allow all (for development)
            return view_func(request, *args, **kwargs)

        if api_key != expected_key:
            return JsonResponse({"error": "Invalid API key"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper


@require_GET
def get_classes(request):
    """
    GET /api/chatbot/classes/

    Returns upcoming bookable class instances.
    No auth required (public schedule info).
    """
    now = timezone.now()

    # Get OPEN and FULL classes that haven't started yet
    instances = ClassInstance.objects.filter(
        status__in=["OPEN", "FULL"]
    ).order_by("date", "start_time")

    classes = []
    for instance in instances:
        # Combine date and time for comparison
        class_dt = timezone.make_aware(
            datetime.combine(instance.date, instance.start_time)
        )

        if class_dt <= now:
            continue

        class_name = instance.class_schedule.class_obj.name

        # Determine subscription requirement
        name_lower = class_name.lower()
        if "semi private" in name_lower:
            requires = "gold"
        elif "kelas pemula" in name_lower:
            requires = "silver"
        else:
            requires = ""

        classes.append({
            "id": instance.id,
            "class_name": class_name,
            "date": instance.date.isoformat(),
            "start_time": instance.start_time.strftime("%H:%M"),
            "end_time": instance.end_time.strftime("%H:%M"),
            "status": instance.status,
            "available_slots": instance.available_slots,
            "max_members": instance.class_schedule.class_obj.max_members,
            "requires": requires,
        })

    return JsonResponse(classes, safe=False)


@require_GET
@api_key_required
def get_member(request):
    """
    GET /api/chatbot/member/?phone=628xxx

    Returns member info by phone number.
    Requires API key (contains member data).
    """
    phone = request.GET.get("phone", "")

    if not phone:
        return JsonResponse({"error": "Phone number required"}, status=400)

    try:
        member = Member.objects.get(phone_number=phone)
    except Member.DoesNotExist:
        return JsonResponse({"error": "Member not found"}, status=404)

    # Check active status
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    is_active = member.active_until and member.active_until >= today_start
    can_book_pemula = member.pemula_active_until and member.pemula_active_until >= today_start
    can_book_semi_private = member.semi_private_active_until and member.semi_private_active_until >= today_start

    return JsonResponse({
        "id": member.id,
        "name": member.name,
        "phone_number": member.phone_number,
        "is_active": is_active,
        "can_book_pemula": can_book_pemula,
        "can_book_semi_private": can_book_semi_private,
    })


@csrf_exempt
@require_POST
@api_key_required
def book_class(request):
    """
    POST /api/chatbot/book/

    Book a class for a member.
    Body: {"member_id": 1, "class_instance_id": 123}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    member_id = data.get("member_id")
    class_instance_id = data.get("class_instance_id")

    if not member_id or not class_instance_id:
        return JsonResponse({"error": "member_id and class_instance_id required"}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "Member not found"}, status=404)

    try:
        instance = ClassInstance.objects.get(id=class_instance_id)
    except ClassInstance.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found"}, status=404)

    # Check if already booked or waitlisted
    if member in instance.booked_members.all():
        return JsonResponse({
            "success": False,
            "message": "You're already booked for this class"
        })

    if member in instance.waitlisted_members.all():
        return JsonResponse({
            "success": False,
            "message": "You're already on the waitlist for this class"
        })

    # Check subscription for special classes
    class_name = instance.class_schedule.class_obj.name.lower()
    class_date_start = timezone.make_aware(
        datetime.combine(instance.date, datetime.min.time())
    )

    if "semi private" in class_name:
        if not member.semi_private_active_until or member.semi_private_active_until < class_date_start:
            return JsonResponse({
                "success": False,
                "message": "Your Gold membership isn't active for this date"
            })

    if "kelas pemula" in class_name:
        if not member.pemula_active_until or member.pemula_active_until < class_date_start:
            return JsonResponse({
                "success": False,
                "message": "Your Silver membership isn't active for this date"
            })

    # Check if class is full
    if instance.booked_members.count() >= instance.class_schedule.class_obj.max_members:
        return JsonResponse({
            "success": False,
            "message": "Class is full. Please join the waitlist instead."
        })

    # Book the class
    instance.booked_members.add(member)
    instance.update_status()

    return JsonResponse({
        "success": True,
        "message": "Booking confirmed",
        "booking_id": instance.id,
    })


@csrf_exempt
@require_POST
@api_key_required
def join_waitlist(request):
    """
    POST /api/chatbot/waitlist/

    Add member to class waitlist.
    Body: {"member_id": 1, "class_instance_id": 123}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    member_id = data.get("member_id")
    class_instance_id = data.get("class_instance_id")

    if not member_id or not class_instance_id:
        return JsonResponse({"error": "member_id and class_instance_id required"}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "Member not found"}, status=404)

    try:
        instance = ClassInstance.objects.get(id=class_instance_id)
    except ClassInstance.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found"}, status=404)

    # Check if already booked or waitlisted
    if member in instance.booked_members.all():
        return JsonResponse({
            "success": False,
            "message": "You're already booked for this class"
        })

    if member in instance.waitlisted_members.all():
        return JsonResponse({
            "success": False,
            "message": "You're already on the waitlist"
        })

    # Add to waitlist
    instance.waitlisted_members.add(member)

    return JsonResponse({
        "success": True,
        "message": "Added to waitlist",
    })


@csrf_exempt
@require_POST
@api_key_required
def cancel_booking(request):
    """
    POST /api/chatbot/cancel/

    Cancel a class booking or leave waitlist.
    Body: {"member_id": 1, "class_instance_id": 123}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    member_id = data.get("member_id")
    class_instance_id = data.get("class_instance_id")

    if not member_id or not class_instance_id:
        return JsonResponse({"error": "member_id and class_instance_id required"}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "Member not found"}, status=404)

    try:
        instance = ClassInstance.objects.get(id=class_instance_id)
    except ClassInstance.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found"}, status=404)

    # Check if booked
    if member in instance.booked_members.all():
        instance.booked_members.remove(member)

        # Move first waitlisted member to booked if space available
        if instance.waitlisted_members.exists():
            max_members = instance.class_schedule.class_obj.max_members
            if instance.booked_members.count() < max_members:
                next_member = instance.waitlisted_members.first()
                instance.waitlisted_members.remove(next_member)
                instance.booked_members.add(next_member)

        instance.update_status()

        return JsonResponse({
            "success": True,
            "message": "Booking cancelled",
        })

    # Check if on waitlist
    if member in instance.waitlisted_members.all():
        instance.waitlisted_members.remove(member)
        return JsonResponse({
            "success": True,
            "message": "Removed from waitlist",
        })

    return JsonResponse({
        "success": False,
        "message": "You don't have a booking for this class",
    })


@require_GET
@api_key_required
def get_my_bookings(request):
    """
    GET /api/chatbot/my-bookings/?member_id=1

    Returns all bookings and waitlist entries for a member.
    """
    member_id = request.GET.get("member_id", "")

    if not member_id:
        return JsonResponse({"error": "member_id required"}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({"error": "Member not found"}, status=404)

    now = timezone.now()
    bookings = []

    # Get booked classes
    booked_instances = member.booked_classes.filter(
        status__in=["OPEN", "FULL"]
    ).order_by("date", "start_time")

    for instance in booked_instances:
        class_dt = timezone.make_aware(
            datetime.combine(instance.date, instance.start_time)
        )
        if class_dt <= now:
            continue

        bookings.append({
            "id": instance.id,
            "class_name": instance.class_schedule.class_obj.name,
            "date": instance.date.isoformat(),
            "start_time": instance.start_time.strftime("%H:%M"),
            "end_time": instance.end_time.strftime("%H:%M"),
            "booking_status": "booked",
        })

    # Get waitlisted classes
    waitlisted_instances = member.waitlisted_classes.filter(
        status__in=["OPEN", "FULL"]
    ).order_by("date", "start_time")

    for instance in waitlisted_instances:
        class_dt = timezone.make_aware(
            datetime.combine(instance.date, instance.start_time)
        )
        if class_dt <= now:
            continue

        bookings.append({
            "id": instance.id,
            "class_name": instance.class_schedule.class_obj.name,
            "date": instance.date.isoformat(),
            "start_time": instance.start_time.strftime("%H:%M"),
            "end_time": instance.end_time.strftime("%H:%M"),
            "booking_status": "waitlisted",
        })

    return JsonResponse(bookings, safe=False)
