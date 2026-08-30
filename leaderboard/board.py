"""Papan Peringkat: points from what members already do, counted on the fly.

There is no table behind this and no nightly snapshot. Every number is derived
from visits, class attendance, quiz answers and no-shows, and the whole board is
one query cached for a few minutes. Two reasons:

1. **Nothing to keep in sync.** Delete a bogus visit and the board is correct on
   the next refresh, including last month's. That is also the fix for anyone who
   games it: correct the member's data, not the scoreboard.
2. **No storage.** The tables it reads are small (about 10k visits, 6k bookings),
   Postgres does the lot in milliseconds, and a year of new data adds nothing.

It is for fun and encouragement, not a ranking anybody should defend. Members see
their own points but not their rank: a beginner discovering they are 78th is not
encouraged by it, and the monthly board resets so newcomers can win something.
"""

from datetime import date

from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from accounts.dates import MONTHS_ID

# What each thing is worth. Visits dominate on purpose: turning up is the
# behaviour worth rewarding, and everything else is a bonus on top.
POINTS = {
    "visits": 8,
    "classes": 2,  # booked a class and actually came that day
    "gizi": 2,  # a Belajar Gizi question answered right the first time
    "daily": 1,  # a Kuis Harian question answered right
    "misses": -10,  # a day with a booked class and no show
}

# The board starts here. Nothing before it: the point system did not exist, and
# half of what it counts was not being recorded yet.
EARLIEST_MONTH = date(2026, 8, 1)

# Long enough that a page refresh is not a fresh query, short enough that a
# member who just checked in sees it move while they are still in the gym.
CACHE_SECONDS = 5 * 60

LIFETIME_KEY = "lifetime"

# One statement for all five sources, so the board is a single round trip.
#
# The null guards let the same SQL serve a month and all time: passing None for
# both dates drops every date predicate. Postgres does not care at this size, and
# it beats maintaining two near-identical queries.
#
# `gizi` takes each member's *first* answer per question before filtering by
# date, so retaking a chapter can never pay twice, and a question always scores
# in the month it was first answered.
BOARD_SQL = """
with visits as (
    select v.member_id, count(*) as n
    from visits_visit v
    where (%(start)s::date is null
           or (v.check_in_time at time zone 'Asia/Jakarta')::date >= %(start)s::date)
      and (%(end)s::date is null
           or (v.check_in_time at time zone 'Asia/Jakarta')::date <= %(end)s::date)
    group by 1
),
attended as (
    select bm.member_id, count(*) as n
    from classes_classinstance_booked_members bm
    join classes_classinstance ci on ci.id = bm.classinstance_id
    where ci.status <> 'CANCELLED'
      and ci.date <= current_date
      and (%(start)s::date is null or ci.date >= %(start)s::date)
      and (%(end)s::date is null or ci.date <= %(end)s::date)
      and exists (
          select 1 from visits_visit v
          where v.member_id = bm.member_id
            and (v.check_in_time at time zone 'Asia/Jakarta')::date = ci.date
      )
    group by 1
),
gizi as (
    select f.member_id, count(*) as n
    from (
        select distinct on (member_id, question_key)
               member_id, question_key, is_correct, created_at
        from nutrition_quizanswer
        order by member_id, question_key, created_at, id
    ) f
    where f.is_correct
      and (%(start)s::date is null
           or (f.created_at at time zone 'Asia/Jakarta')::date >= %(start)s::date)
      and (%(end)s::date is null
           or (f.created_at at time zone 'Asia/Jakarta')::date <= %(end)s::date)
    group by 1
),
daily as (
    select member_id, count(*) as n
    from nutrition_dailyanswer
    where is_correct
      and (%(start)s::date is null or answer_date >= %(start)s::date)
      and (%(end)s::date is null or answer_date <= %(end)s::date)
    group by 1
),
misses as (
    select member_id, count(distinct class_date) as n
    from classes_classmiss
    where (%(start)s::date is null or class_date >= %(start)s::date)
      and (%(end)s::date is null or class_date <= %(end)s::date)
    group by 1
)
select m.id,
       m.name,
       coalesce(visits.n, 0) as visits,
       coalesce(attended.n, 0) as classes,
       coalesce(gizi.n, 0) as gizi,
       coalesce(daily.n, 0) as daily,
       coalesce(misses.n, 0) as misses
from accounts_member m
left join visits on visits.member_id = m.id
left join attended on attended.member_id = m.id
left join gizi on gizi.member_id = m.id
left join daily on daily.member_id = m.id
left join misses on misses.member_id = m.id
where coalesce(visits.n, 0) + coalesce(attended.n, 0) + coalesce(gizi.n, 0)
      + coalesce(daily.n, 0) + coalesce(misses.n, 0) > 0
"""


def display_name(name):
    """"Cornelius Yan Mintareja" -> "Cornelius Y. M."

    First name in full, everything after it as initials. Members recognise each
    other without the board publishing a full name next to somebody's attendance
    record. A one-word name is left alone.
    """
    parts = (name or "").split()
    if not parts:
        return "Member"
    initials = [f"{part[0].upper()}." for part in parts[1:] if part]
    return " ".join([parts[0]] + initials)


def month_label(year, month):
    return f"{MONTHS_ID[month]} {year}"


def month_period(year, month):
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1) - timezone.timedelta(days=1)
    return {
        "key": f"{year:04d}-{month:02d}",
        "label": month_label(year, month),
        "short": MONTHS_ID[month],
        "start": start,
        "end": end,
        "is_lifetime": False,
    }


def lifetime_period():
    return {
        "key": LIFETIME_KEY,
        "label": "Sepanjang Waktu",
        "short": "Sepanjang Waktu",
        "start": None,
        "end": None,
        "is_lifetime": True,
    }


def months_available(today=None):
    """Every month with a board, newest first, from EARLIEST_MONTH to now."""
    today = today or timezone.localdate()
    months = []
    year, month = EARLIEST_MONTH.year, EARLIEST_MONTH.month
    while (year, month) <= (today.year, today.month):
        months.append(month_period(year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    months.reverse()
    return months


def resolve_period(key, today=None):
    """Turn a URL parameter into a period, falling back to the current month.

    Anything unrecognised becomes this month rather than an error: the value comes
    from a query string and a wrong one should not be a 500.
    """
    today = today or timezone.localdate()
    if key == LIFETIME_KEY:
        return lifetime_period()

    if key:
        try:
            year, month = (int(part) for part in key.split("-", 1))
            if (year, month) >= (EARLIEST_MONTH.year, EARLIEST_MONTH.month) and (
                year,
                month,
            ) <= (today.year, today.month):
                return month_period(year, month)
        except (ValueError, TypeError, IndexError):
            pass

    return month_period(today.year, today.month)


def _score(row):
    return sum(row[key] * points for key, points in POINTS.items())


def compute(period):
    """Every member with any activity in the period, best first.

    Ranks are competition style: two members on the same total share a rank and
    the next one down skips a number.
    """
    with connection.cursor() as cursor:
        cursor.execute(BOARD_SQL, {"start": period["start"], "end": period["end"]})
        raw = cursor.fetchall()

    rows = []
    for member_id, name, visits, classes, gizi, daily, misses in raw:
        counts = {
            "visits": visits,
            "classes": classes,
            "gizi": gizi,
            "daily": daily,
            "misses": misses,
        }
        rows.append(
            {
                "member_id": member_id,
                "name": display_name(name),
                "initial": (name or "?").strip()[:1].upper(),
                "counts": counts,
                "points": {key: counts[key] * value for key, value in POINTS.items()},
                "total": _score(counts),
            }
        )

    rows.sort(key=lambda row: (-row["total"], row["name"]))

    # `share` drives the bar behind each row: how far along the leader's total
    # this member is. Clamped, since a member deep in penalty points is negative
    # and a bar cannot be.
    leader = max((row["total"] for row in rows), default=0)

    rank = 0
    previous = None
    for index, row in enumerate(rows, start=1):
        if row["total"] != previous:
            rank = index
            previous = row["total"]
        row["rank"] = rank
        row["share"] = (
            max(0, min(100, round(row["total"] * 100 / leader))) if leader > 0 else 0
        )
    return rows


def board(period, top=30, member=None):
    """The cached board, plus the current member's own row.

    Cached whole rather than per member: it is the same table for everybody, and
    the member's own line comes out of the same snapshot so the two can never
    contradict each other.
    """
    cache_key = f"leaderboard:{period['key']}"
    rows = cache.get(cache_key)
    if rows is None:
        rows = compute(period)
        cache.set(cache_key, rows, CACHE_SECONDS)

    mine = None
    if member:
        mine = next(
            (row for row in rows if row["member_id"] == member.id),
            {
                "member_id": member.id,
                "name": display_name(member.name),
                "initial": (member.name or "?").strip()[:1].upper(),
                "counts": {key: 0 for key in POINTS},
                "points": {key: 0 for key in POINTS},
                "total": 0,
                "rank": None,
            },
        )

    return {
        "period": period,
        "podium": rows[:3],
        "rest": rows[3:top],
        "rows": rows[:top],
        "total_members": len(rows),
        "mine": mine,
        "mine_in_top": bool(mine and any(r["member_id"] == mine["member_id"] for r in rows[:top])),
    }
