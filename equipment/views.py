from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from .models import Equipment
from collections import defaultdict
import re

# Create your views here.


def is_likely_bot(request):
    """
    Simple bot detection based on user agent patterns.
    Returns True if the request is likely from a bot/crawler.
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

    # Common bot patterns
    bot_patterns = [
        r"bot",
        r"crawler",
        r"spider",
        r"scraper",
        r"scrapy",  # Add scrapy specifically
        r"fetch",
        r"monitor",
        r"curl",
        r"wget",
        r"python",
        r"java",
        r"go-http",
        r"okhttp",
        r"facebookexternalhit",
        r"twitterbot",
        r"linkedinbot",
        r"whatsapp",
        r"telegram",
        r"discord",
        r"slack",
        r"googlebot",
        r"bingbot",
        r"yandexbot",
        r"baiduspider",
        r"duckduckbot",
        r"applebot",
    ]

    for pattern in bot_patterns:
        if re.search(pattern, user_agent):
            return True

    # Check if user agent is suspiciously short or missing
    if len(user_agent) < 10:
        return True

    return False


def should_count_view(request, equipment_slug, cooldown_hours=24):
    """
    Determine if this view should be counted based on time-based tracking
    and bot detection.

    Args:
        request: Django request object
        equipment_slug: Equipment slug identifier
        cooldown_hours: Hours to wait before counting same user again (default: 24)
    """
    # Skip bots
    if is_likely_bot(request):
        return False

    # Time-based deduplication (count once per cooldown period per equipment)
    session_key = f"viewed_equipment_{equipment_slug}_last_time"
    import time

    last_view_time = request.session.get(session_key, 0)
    current_time = time.time()

    # If last view was less than cooldown period ago, don't count
    cooldown_seconds = cooldown_hours * 60 * 60
    if current_time - last_view_time < cooldown_seconds:
        return False

    # Mark current time as last viewed
    request.session[session_key] = current_time

    return True


@cache_page(60 * 60 * 4)  # Cache for 4 hours
def equipment_list(request):
    # Try to get cached data first
    cache_key = "equipment_grouped_list"
    grouped_equipments = cache.get(cache_key)

    if grouped_equipments is None:
        # Cache miss - fetch from database
        equipments = Equipment.objects.order_by("muscle_group", "name")
        grouped_equipments = defaultdict(list)
        for equipment in equipments:
            muscle_group = equipment.muscle_group or "Lainnya"
            grouped_equipments[muscle_group].append(equipment)

        # Convert to regular dict and cache for 12 hours
        grouped_equipments = dict(grouped_equipments)
        cache.set(cache_key, grouped_equipments, 60 * 60 * 12)

    context = {"grouped_equipments": grouped_equipments}
    return render(request, "equipment/list.html", context)


def equipment_detail(request, slug):
    equipment = get_object_or_404(Equipment, slug=slug)

    # Track view if it should be counted
    if should_count_view(request, slug):
        # Check if user is authenticated (logged in members)
        is_authenticated = (
            hasattr(request, "session")
            and request.session.get("member_email") is not None
        )

        # Increment view count
        equipment.increment_view_count(is_authenticated=is_authenticated)

    return render(request, "equipment/detail.html", {"equipment": equipment})
