"""The live numbers the homepage makes its case with.

"3 dari 4 member kami mulai dari nol", "maks 6 orang", "94% bilang Mantap": each
one is a claim to somebody deciding whether they are brave enough to come, so it
is read from the data rather than typed into the template, where it would stay
true for a few months and then quietly stop being true.

Cached for a few hours, since none of these move within a day and the homepage
is also the deploy health check: it has to stay cheap. Guarded like the reviews
strip, because a release that adds a table serves new code before migrations
finish. A failed read is not cached, so the next request simply tries again.
"""

import logging

from django.core.cache import cache
from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q

logger = logging.getLogger(__name__)

CACHE_KEY = "homepage:stats:v1"
CACHE_SECONDS = 6 * 60 * 60

# Below these, a percentage is an anecdote, so the claim is left out.
MIN_MEMBERS = 50
MIN_CLASS_REVIEWS = 50

# A number is only printed while it still makes the case. Below these the page
# falls back to wording with no number, instead of advertising "40% Mantap".
MIN_PEMULA_SHARE = 0.5
MIN_MANTAP_PERCENT = 80
MIN_FEMALE_PERCENT = 40

# "3 dari 4" only when the share really is about three quarters.
QUARTER_TOLERANCE = 0.03


def share_in_words(part, total):
    """A share the way you would say it out loud: "3 dari 4", "separuh", "62%"."""
    if not total:
        return None
    share = part / total
    for quarters, words in ((1, "1 dari 4"), (2, "separuh"), (3, "3 dari 4")):
        if abs(share - quarters / 4) <= QUARTER_TOLERANCE:
            return words
    return f"{round(share * 100)}%"


def _percent(part, total):
    return round(100 * part / total) if total else None


def _compute():
    from accounts.models import Member
    from classes.models import Class, ClassReview
    from equipment.models import Equipment

    members = Member.objects.aggregate(
        total=Count("id"),
        # is_pemula can be empty; an unknown is neither a first-timer nor not one
        known=Count("id", filter=Q(is_pemula__isnull=False)),
        pemula=Count("id", filter=Q(is_pemula=True)),
        female=Count("id", filter=Q(gender="F")),
    )
    pemula_share = None
    if members["known"] >= MIN_MEMBERS and members["pemula"] / members["known"] >= MIN_PEMULA_SHARE:
        pemula_share = share_in_words(members["pemula"], members["known"])
    female_percent = (
        _percent(members["female"], members["total"]) if members["total"] >= MIN_MEMBERS else None
    )

    # Same name match the booking rules use to tell the class types apart, and
    # only classes still on the schedule: a retired class must not set the cap.
    caps = list(
        Class.objects.filter(schedules__isnull=False)
        .distinct()
        .values_list("name", "max_members")
    )
    pemula_caps = [cap for name, cap in caps if "kelas pemula" in name.lower()]
    semi_caps = [cap for name, cap in caps if "semi private" in name.lower()]

    reviews = ClassReview.objects.filter(rating__isnull=False).aggregate(
        rated=Count("id"),
        mantap=Count("id", filter=Q(rating=ClassReview.MANTAP)),
    )
    mantap_percent = None
    if reviews["rated"] >= MIN_CLASS_REVIEWS:
        mantap_percent = _percent(reviews["mantap"], reviews["rated"])
        if mantap_percent < MIN_MANTAP_PERCENT:
            mantap_percent = None

    equipment = Equipment.objects.aggregate(
        total=Count("id"),
        with_video=Count("id", filter=Q(video_link__gt="")),
    )

    return {
        "pemula_share": pemula_share,
        "female_percent": (
            female_percent if female_percent and female_percent >= MIN_FEMALE_PERCENT else None
        ),
        "pemula_class_size": max(pemula_caps) if pemula_caps else None,
        "semi_private_size": max(semi_caps) if semi_caps else None,
        "mantap_percent": mantap_percent,
        "class_reviews": reviews["rated"],
        "equipment_total": equipment["total"],
        "equipment_all_have_video": (
            equipment["total"] > 0 and equipment["with_video"] == equipment["total"]
        ),
    }


def homepage_stats():
    """The numbers above, or {} when the database cannot answer right now."""
    stats = cache.get(CACHE_KEY)
    if stats is not None:
        return stats
    try:
        stats = _compute()
    except (ProgrammingError, OperationalError):
        logger.warning(
            "Homepage numbers skipped: database not ready, migrations may still be running",
            exc_info=True,
        )
        return {}
    cache.set(CACHE_KEY, stats, CACHE_SECONDS)
    return stats
