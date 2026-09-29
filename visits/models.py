from datetime import datetime, time

from django.db import models
from django.utils import timezone

from accounts.models import Member, start_of_local_day

# Where a visit nobody checked out of is closed: the end of its own day. The
# real time is unknown, and 23:59 keeps the visit on the day it happened.
FORGOTTEN_CHECK_OUT_AT = time(23, 59)


class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, db_index=True)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-check_in_time"]
        indexes = [
            models.Index(
                fields=["member", "check_in_time"], name="visit_member_checkin_idx"
            ),
            models.Index(fields=["check_in_time"], name="visit_checkin_idx"),
        ]


def close_forgotten_visits(member, today=None):
    """Close this member's visits left open on an earlier day, at 23:59 that day.

    The next check-in used to reuse such a visit, so that day recorded no
    check-in at all, and a class booked for it counted as missed (see
    classes/attendance.py). Check-in and check-out both call this first.
    Returns how many were closed.
    """
    today = today or timezone.localdate()
    forgotten = Visit.objects.filter(
        member=member,
        check_out_time__isnull=True,
        check_in_time__lt=start_of_local_day(today),
    )
    closed = 0
    for visit in forgotten:
        end_of_day = timezone.make_aware(
            datetime.combine(timezone.localdate(visit.check_in_time), FORGOTTEN_CHECK_OUT_AT)
        )
        visit.check_out_time = max(end_of_day, visit.check_in_time)
        visit.save(update_fields=["check_out_time"])
        closed += 1
    return closed
