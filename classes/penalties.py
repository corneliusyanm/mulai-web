"""Waste a booked seat too often and class booking locks for a few days.

Why it exists: a handful of members book several classes a week and waste a third
of them, which holds slots nobody else can take. The daily cap stopped the
hoarding; this is for the wasting.

A seat gets wasted two ways, and they count the same because they cost the same:

- **Nggak dateng.** Booked, class ran, never checked in. Found by the nightly
  command after the gym closes, when a booking either got attended or it did not
  and we do not have to guess about someone who is merely late.
- **Batalin mepet.** Cancelled inside `late_cancel_hours` of the start. Written
  by `record_late_cancel` the moment it happens, since there is nothing left to
  find out: that close in, the seat is not getting filled by anybody who was not
  already coming.

Four deliberate choices:

1. **Strikes are counted per day, not per class.** One lie-in with two classes
   booked is one strike. It reads as fairer, and with the daily cap the
   difference is small.
2. **Nothing before `PenaltySettings.effective_from` counts.** Members are not
   punished for behaviour from before the rule existed.
3. **Only bookings *after* the evening being processed are cancelled.** Today's
   bookings stay: their misses were just recorded, and deleting them would erase
   the evidence from the admin's no-show report.
4. **A late cancel does not lock anyone on the spot.** It writes the strike and
   the nightly run does the arithmetic, same as every other miss. One place
   decides who gets locked, and a member is never banned mid-tap.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import Member
from reminders.models import Reminder

from .attendance import no_show_scan
from .models import (
    BookingPenalty,
    ClassInstance,
    ClassMiss,
    PenaltySettings,
    WaitlistPromotion,
    cancel_deadline_at,
)


def record_misses(day, settings=None):
    """Write a ClassMiss for every booking on `day` that was not attended.

    Idempotent: the unique constraint on (member, class instance) means running
    the command twice on the same evening records nothing new.
    """
    settings = settings or PenaltySettings.get_solo()
    if day < settings.effective_from:
        return []

    scan = no_show_scan(day, day, today=day)
    recorded = []
    for member, instance in scan["missed"]:
        miss, created = ClassMiss.objects.get_or_create(
            member=member,
            class_instance=instance,
            defaults={
                "class_date": instance.date,
                "class_name": instance.class_schedule.class_obj.name,
                "class_start_time": instance.start_time,
            },
        )
        if created:
            recorded.append(miss)
    return recorded


def record_late_cancel(member, instance, now=None, settings=None):
    """Write a strike for cancelling inside the deadline, or return None.

    The one miss that is not written by the nightly command, because by the time
    a member taps Batalkan there is nothing left to find out: four hours before
    the class, that seat is not getting filled by anybody who was not already
    coming. Writing it here also means the member is told the consequence in the
    same breath as the action, instead of discovering it the next morning.

    It is still an ordinary ClassMiss, so the window count, the ban, the card on
    /akun, the admin report and Papan Peringkat all treat it like a no-show
    without knowing it exists.

    Never a strike when: the penalty is off, the class is older than the rule,
    the gym itself cancelled the class, the deadline has not passed, or the
    member only got this booking by being promoted off the waitlist after the
    deadline, which is a seat nobody told them they had.
    """
    settings = settings or PenaltySettings.get_solo()
    now = now or timezone.now()

    if not settings.enabled or instance.date < settings.effective_from:
        return None
    if instance.status == "CANCELLED":
        return None

    deadline = cancel_deadline_at(instance, settings)
    if now < deadline:
        return None
    if WaitlistPromotion.objects.filter(
        member=member, class_instance=instance, promoted_at__gte=deadline
    ).exists():
        return None

    miss, _ = ClassMiss.objects.get_or_create(
        member=member,
        class_instance=instance,
        defaults={
            "class_date": instance.date,
            "class_name": instance.class_schedule.class_obj.name,
            "class_start_time": instance.start_time,
            "kind": "LATE_CANCEL",
        },
    )
    return miss


def miss_days_in_window(member, day, settings=None):
    """How many distinct days this member missed a class inside the window.

    Counted per day, so two classes missed on one date is one.
    """
    settings = settings or PenaltySettings.get_solo()
    window_start = max(
        day - timedelta(days=settings.window_days - 1), settings.effective_from
    )
    days = (
        ClassMiss.objects.filter(
            member=member, class_date__gte=window_start, class_date__lte=day
        )
        .values_list("class_date", flat=True)
        .distinct()
    )
    return len(set(days))


def _clear_future_bookings(member, first_day, blocked_until):
    """Drop the member's bookings and waitlist places inside the locked days.

    Cancelling promotes whoever is next on the waitlist, which is the whole
    point: the slot goes to someone who will use it.
    """
    cancelled = 0
    waitlists = 0

    booked = ClassInstance.objects.filter(
        booked_members=member, date__gte=first_day, date__lt=blocked_until
    ).exclude(status="CANCELLED")
    for instance in booked:
        instance.booked_members.remove(member)
        instance.move_from_waitlist()
        instance.update_status()
        cancelled += 1

    waitlisted = ClassInstance.objects.filter(
        waitlisted_members=member, date__gte=first_day, date__lt=blocked_until
    ).exclude(status="CANCELLED")
    for instance in waitlisted:
        instance.waitlisted_members.remove(member)
        waitlists += 1

    return cancelled, waitlists


def _staff_reminder(member, penalty):
    """Put it in the staff queue: the member has no notification channel.

    Their bookings vanish overnight and the only explanation is a card on /akun
    they may never open, so somebody should be able to text them.
    """
    Reminder.objects.get_or_create(
        member=member,
        reminder_type="PENALTI_KELAS",
        due_date=penalty.starts_on,
        defaults={
            "reason": (
                f"{member.name} buang tempat kelas {penalty.miss_days} kali dalam "
                f"{PenaltySettings.get_solo().window_days} hari terakhir (nggak "
                f"dateng atau batalin mepet). Booking "
                f"kelas dikunci sampai {penalty.blocked_until:%d %b %Y}"
                + (
                    f", {penalty.bookings_cancelled} booking dibatalkan"
                    if penalty.bookings_cancelled
                    else ""
                )
                + ". Kabarin ya, biar nggak bingung bookingnya hilang."
            )
        },
    )


@transaction.atomic
def apply_penalties(day=None, dry_run=False):
    """Record the evening's misses and lock anyone who went over the allowance.

    Returns a report the management command prints. Safe to run twice: misses are
    unique per booking and a penalty is unique per member per day.
    """
    settings = PenaltySettings.get_solo()
    day = day or timezone.localdate()
    report = {
        "day": day,
        "enabled": settings.enabled,
        "before_effective_from": day < settings.effective_from,
        "misses_recorded": 0,
        "penalties": [],
        "skipped_existing": 0,
        "dry_run": dry_run,
        "settings": settings,
    }

    if not settings.enabled or day < settings.effective_from:
        return report

    report["misses_recorded"] = len(record_misses(day, settings))

    # Everyone who missed a class today, not only the rows this run happened to
    # create. Same set on a first run, and on a second run it means the evening
    # is re-evaluated rather than skipped, so a half-finished run can be redone.
    missed_today = Member.objects.filter(class_misses__class_date=day).distinct()
    for member in missed_today:
        count = miss_days_in_window(member, day, settings)
        if count <= settings.misses_allowed:
            continue

        if BookingPenalty.objects.filter(member=member, starts_on=day).exists():
            report["skipped_existing"] += 1
            continue

        blocked_until = day + timedelta(days=settings.ban_days)
        # Never shorten a penalty already running: extend to whichever ends later.
        if member.booking_blocked_until and member.booking_blocked_until > blocked_until:
            blocked_until = member.booking_blocked_until

        # Today's bookings stay: their misses were just recorded above, and
        # removing them would erase the evidence from the no-show report.
        cancelled, waitlists = _clear_future_bookings(
            member, day + timedelta(days=1), blocked_until
        )

        penalty = BookingPenalty(
            member=member,
            starts_on=day,
            blocked_until=blocked_until,
            miss_days=count,
            bookings_cancelled=cancelled,
            waitlists_cleared=waitlists,
        )
        report["penalties"].append(penalty)

        if dry_run:
            continue

        penalty.save()
        member.booking_blocked_until = blocked_until
        member.save(update_fields=["booking_blocked_until"])
        _staff_reminder(member, penalty)

    if dry_run:
        transaction.set_rollback(True)
    return report


def member_state(member, today=None):
    """What /akun should say about this member's no-show record, or None.

    None means they have never missed a booked class, and the whole section stays
    off their page: most members should never learn this feature exists.

    Levels: `banned` while booking is locked, `pending` when they are already
    over the allowance and tonight's run will lock them, `warning` on their last
    free strike, `history` for a member with a miss or two and nothing hanging
    over them.

    `pending` exists because a late cancellation is recorded the moment it
    happens while the lock is only applied at 21:00. Without it a member who has
    just gone over reads the calm history line, books two more classes, and finds
    them gone in the morning with no idea why.
    """
    settings = PenaltySettings.get_solo()
    today = today or timezone.localdate()

    misses = list(
        ClassMiss.objects.filter(member=member).order_by("-class_date")[:5]
    )
    if not misses:
        return None

    in_window = miss_days_in_window(member, today, settings)
    penalty = (
        BookingPenalty.objects.filter(member=member).order_by("-starts_on").first()
    )
    locked = member.booking_locked(today)

    # Over the allowance is not enough on its own: a member who already served a
    # lock for these same misses is done with them. What makes it pending is a
    # miss the nightly run has not seen yet, so their newest miss is more recent
    # than any penalty they have been given.
    latest_miss = misses[0].class_date
    unprocessed = not BookingPenalty.objects.filter(
        member=member, starts_on__gte=latest_miss
    ).exists()

    if locked:
        level = "banned"
    elif settings.enabled and in_window > settings.misses_allowed and unprocessed:
        level = "pending"
    elif settings.enabled and in_window == settings.misses_allowed:
        level = "warning"
    else:
        level = "history"

    return {
        "level": level,
        "misses_in_window": in_window,
        "misses_allowed": settings.misses_allowed,
        "window_days": settings.window_days,
        "ban_days": settings.ban_days,
        "late_cancel_hours": settings.late_cancel_hours,
        "blocked_until": member.booking_blocked_until if locked else None,
        "penalty": penalty if locked else None,
        "recent_misses": misses,
        "total_misses": ClassMiss.objects.filter(member=member).count(),
    }
