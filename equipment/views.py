from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from . import guide
from .models import Equipment
import re


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


@require_POST
def equipment_seen(request, slug):
    """Count one view of a machine page, reported by the page itself.

    Counting on the GET counted anything that fetched the URL: scrapers with a
    browser user agent, link previews, prefetches. Since those keep no cookies,
    every fetch was a new session and the 24-hour dedupe never caught them.
    Now the page's script reports the view once it has been on screen for a few
    seconds. That needs JavaScript, a visible page, and the CSRF cookie and
    token from a real page load, which rules out almost everything automated.
    The user agent check and the per-session dedupe still apply on top.
    """
    equipment = get_object_or_404(Equipment, slug=slug)
    if should_count_view(request, slug):
        equipment.increment_view_count(
            is_authenticated=request.session.get("member_email") is not None
        )
    return HttpResponse(status=204)


@cache_page(60 * 60 * 4)  # Cache for 4 hours
def equipment_list(request):
    equipments = list(Equipment.objects.order_by("name"))
    groups = guide.grouped(equipments)
    context = {
        "groups": groups,
        "group_counts": {group["id"]: len(group["items"]) for group in groups},
        "starter": guide.starter(equipments),
        "total": len(equipments),
        # a link that is not a YouTube video has no player, so it does not count
        "all_have_video": bool(equipments) and all(e.get_youtube_embed_url() for e in equipments),
    }
    return render(request, "equipment/list.html", context)


def equipment_detail(request, slug):
    # Not counted here: see equipment_seen.
    equipment = get_object_or_404(Equipment, slug=slug)
    group = guide.group_name(equipment)
    related = list(
        Equipment.objects.filter(muscle_group=equipment.muscle_group)
        .exclude(pk=equipment.pk)
        .order_by("name")[: guide.RELATED_LIMIT]
    )
    context = {
        "equipment": equipment,
        "how_to": guide.steps(equipment.description),
        "targets": guide.target_muscles(equipment),
        "group_label": guide.group_label(group),
        "group_id": guide.group_id(group),
        "related": related,
        "seo_description": guide.seo_description(equipment),
    }
    return render(request, "equipment/detail.html", context)
