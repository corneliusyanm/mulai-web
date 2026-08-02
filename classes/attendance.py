"""What counts as missing a booked class, defined once.

A member missed a class when they held a booking, the class date has passed, and
they did not check in **at all** that local day. Coming at 19:00 after skipping
the 07:00 class counts as attending. That is deliberately generous: the strict
version would punish everyone who forgot to tap the QR, or whom an admin checked
in ten minutes after the class started, and there is no way to tell those apart
from a real no-show.

Both the admin no-show report and the booking penalty read this module, so the
report an admin quotes to a member and the rule that locks their booking can
never disagree about what happened.
"""

from django.utils import timezone

from visits.models import Visit

from .models import ClassInstance


def visit_days_by_member(start_date, end_date):
    """{member id: {local dates they checked in}} for the range.

    One query for the whole range, since the alternative is a query per booking.
    """
    days = {}
    visits = Visit.objects.filter(
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date,
    ).only("member_id", "check_in_time")
    for visit in visits.iterator():
        local_day = timezone.localtime(visit.check_in_time).date()
        days.setdefault(visit.member_id, set()).add(local_day)
    return days


def no_show_scan(start_date, end_date, today=None):
    """Bookings in the range that were not attended.

    Returns `missed` as (member, instance) pairs, newest class first, plus
    `past_bookings`, the number of bookings in the range whose date has passed,
    which is what a no-show rate needs as its denominator.

    Cancelled classes are excluded: nobody skipped a class that did not run.
    """
    today = today or timezone.localdate()
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    instances = (
        ClassInstance.objects.filter(date__gte=start_date, date__lte=end_date)
        .exclude(status="CANCELLED")
        .select_related("class_schedule__class_obj")
        .prefetch_related("booked_members")
        .order_by("-date", "-start_time")
    )

    visit_days = visit_days_by_member(start_date, end_date)

    missed = []
    past_bookings = 0
    for instance in instances:
        if instance.date > today:
            continue
        booked = list(instance.booked_members.all())
        past_bookings += len(booked)
        for member in booked:
            attended = visit_days.get(member.id)
            if attended and instance.date in attended:
                continue
            missed.append((member, instance))

    return {"missed": missed, "past_bookings": past_bookings}
