"""The one or two lines worth reading on the check-in and check-out screens.

Those screens are up for a few seconds, about 32 times a day, so each line has
to be something the member cares about right then: which visit this is, that
the membership ends this week, how long they trained, when the next class is.
All of it is worked out here so the screens only print it.
"""

from datetime import datetime, timedelta

from django.utils import timezone

from accounts.views import NUDGE_DAYS_BEFORE, VISIT_MILESTONES, _visit_milestone

from .models import Visit

# Outside this range the length says more about the button than the workout.
# In production (180 days) 43 visits were under 5 minutes, which is a check-in
# and check-out in one go, and 25 were over 4 hours, which is a forgotten
# check-out. The other 5,200 sit in between.
WORKOUT_MINUTES_SHOWN = (15, 4 * 60)

# How far ahead a booked class still reads as "the next one".
NEXT_CLASS_DAYS = 14


def visit_moment(member, visit):
    """Which visit this is, and whether that is worth celebrating.

    `kind` is "first" for the very first visit, "milestone" when the number is
    one of the /akun badges (same VISIT_MILESTONES), otherwise "count", which
    comes with how many more to the next badge.
    """
    number = Visit.objects.filter(
        member=member, check_in_time__lte=visit.check_in_time
    ).count()
    if number <= 1:
        kind = "first"
    elif number in VISIT_MILESTONES:
        kind = "milestone"
    else:
        kind = "count"
    progress = _visit_milestone(number) or {}
    return {
        "kind": kind,
        "number": number,
        "next": progress.get("next"),
        "remaining": progress.get("remaining"),
        "percent": progress.get("percent"),
    }


def membership_ending(member, today):
    """{"days", "on"} when the membership ends within the /akun nudge window.

    Same rules as the /akun nudge: nothing for members the admins handle by
    hand (`skip_auto_reminder`), and nothing once it has already ended, since
    an expired member never reaches the success screen.
    """
    if not member.active_until or member.skip_auto_reminder:
        return None
    ends_on = timezone.localdate(member.active_until)
    days = (ends_on - today).days
    if 0 <= days <= NUDGE_DAYS_BEFORE:
        return {"days": days, "on": ends_on}
    return None


def workout_length(visit):
    """"1 jam 22 menit", or "" when the length is not a real workout."""
    if not visit.check_out_time:
        return ""
    minutes = int((visit.check_out_time - visit.check_in_time).total_seconds() // 60)
    shortest, longest = WORKOUT_MINUTES_SHOWN
    if not shortest <= minutes <= longest:
        return ""
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} jam {minutes} menit"
    if hours:
        return f"{hours} jam"
    return f"{minutes} menit"


def next_class(member, now):
    """The next booked class that has not started yet, or None.

    Carries `starts_at` (aware, local) and `day_word`: "nanti" for later today,
    "besok" for tomorrow, None for anything later, where the screen prints the
    date instead. A cancelled class is not a next class.
    """
    today = timezone.localdate(now)
    upcoming = (
        member.booked_classes.filter(
            date__gte=today, date__lte=today + timedelta(days=NEXT_CLASS_DAYS)
        )
        .exclude(status="CANCELLED")
        .select_related("class_schedule__class_obj")
        .order_by("date", "start_time")
    )
    for instance in upcoming[:10]:
        starts_at = timezone.make_aware(datetime.combine(instance.date, instance.start_time))
        if starts_at <= now:
            continue
        instance.starts_at = starts_at
        if instance.date == today:
            instance.day_word = "nanti"
        elif instance.date == today + timedelta(days=1):
            instance.day_word = "besok"
        else:
            instance.day_word = None
        return instance
    return None
