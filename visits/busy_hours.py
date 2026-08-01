"""When is the gym usually quiet?

Members ask this before they come, and for a gym where most people have never
trained before the useful answer is "here are the hours you get the place almost
to yourself", not "it is full right now, stay away". So this returns the quiet
windows, and the copy that uses it points at them.

The numbers are a 12-week average for one weekday, never a live count. A live
count is a scary number with no context (a busy evening here is about 20 people),
and it would change between two page loads for no good reason.
"""

from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay
from django.utils import timezone

from .models import Visit

# Python weekday() (Monday=0) -> (first hour open, hour the gym closes).
# Sunday opens 07:30, so its 07:00 bar only covers half an hour.
OPENING_HOURS = {
    0: (7, 21),
    1: (7, 21),
    2: (7, 21),
    3: (7, 21),
    4: (7, 21),
    5: (7, 20),
    6: (7, 20),
}

# How far back to average. Long enough to smooth out one odd week, short enough
# that it still describes how the gym feels now.
LOOKBACK_WEEKS = 12

# Below this many check-ins for the weekday the average is noise, so say nothing
# rather than send someone at a made-up hour.
MIN_SAMPLE = 20

# Share of the busiest hour, below which an hour counts as quiet / medium.
QUIET_AT_OR_BELOW = 40
MEDIUM_AT_OR_BELOW = 75

DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def hourly_counts(weekday, now=None):
    """Check-ins per local hour for one weekday, averaged over LOOKBACK_WEEKS.

    Cached per weekday per day: the window is 12 weeks, so today's own check-ins
    cannot move it enough to be worth a query on every page load.
    """
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    key = f"visit-hour-counts:{weekday}:{today.isoformat()}"

    counts = cache.get(key)
    if counts is None:
        rows = (
            Visit.objects.filter(
                check_in_time__gte=now - timedelta(weeks=LOOKBACK_WEEKS)
            )
            .annotate(
                local_hour=ExtractHour("check_in_time"),
                local_dow=ExtractIsoWeekDay("check_in_time"),
            )
            .filter(local_dow=weekday + 1)  # ExtractIsoWeekDay: Monday is 1
            .values("local_hour")
            .annotate(total=Count("id"))
        )
        counts = {row["local_hour"]: row["total"] for row in rows}
        cache.set(key, counts, 6 * 60 * 60)
    return counts


def _level(percent):
    if percent <= QUIET_AT_OR_BELOW:
        return "quiet"
    if percent <= MEDIUM_AT_OR_BELOW:
        return "medium"
    return "busy"


def _quietest_window(hours):
    """The longest run of quiet hours, as (start hour, end hour).

    End is exclusive, so a run of 10 and 11 on a gym that closes at 21 reads
    "10:00 - 12:00": the whole 11 o'clock hour is still quiet.
    """
    best = current = None
    for entry in hours:
        if entry["level"] != "quiet":
            current = None
            continue
        if current is None:
            current = {"start": entry["hour"], "end": entry["hour"] + 1, "total": 0}
        current["end"] = entry["hour"] + 1
        current["total"] += entry["count"]
        longer = best is None or (current["end"] - current["start"]) > (
            best["end"] - best["start"]
        )
        quieter = (
            best is not None
            and (current["end"] - current["start"]) == (best["end"] - best["start"])
            and current["total"] < best["total"]
        )
        if longer or quieter:
            best = dict(current)
    if best is None:
        return None
    return best["start"], best["end"]


def quiet_hours(day=None, now=None):
    """Today's quiet-hours strip, or None when there is not enough history.

    Returns the bars to draw, the quietest window, and where "now" sits, all as
    plain values so the template only has to render them.
    """
    now = now or timezone.now()
    local_now = timezone.localtime(now)
    day = day or local_now.date()

    open_hour, close_hour = OPENING_HOURS[day.weekday()]
    counts = hourly_counts(day.weekday(), now=now)
    open_range = range(open_hour, close_hour)

    within_hours = [counts.get(hour, 0) for hour in open_range]
    if sum(within_hours) < MIN_SAMPLE:
        return None

    peak = max(within_hours)
    is_today = day == local_now.date()
    current_hour = local_now.hour if is_today else None

    hours = []
    for hour in open_range:
        count = counts.get(hour, 0)
        percent = round(count / peak * 100) if peak else 0
        hours.append(
            {
                "hour": hour,
                "label": f"{hour:02d}",
                "count": count,
                # Keep a sliver of bar even for an empty hour, so the strip
                # reads as a row of hours rather than a gap.
                "percent": max(percent, 6),
                "level": _level(percent),
                "is_now": hour == current_hour,
                "show_label": hour % 3 == open_hour % 3,
            }
        )

    window = _quietest_window(hours)
    now_level = None
    if current_hour is not None:
        for entry in hours:
            if entry["is_now"]:
                now_level = entry["level"]

    return {
        "hours": hours,
        "day_name": DAYS_ID[day.weekday()],
        "open_hour": open_hour,
        "close_hour": close_hour,
        "now_level": now_level,
        "quietest": (
            {
                "start": window[0],
                "end": window[1],
                "label": f"{window[0]:02d}:00 - {window[1]:02d}:00",
            }
            if window
            else None
        ),
    }
