"""The no-show penalty: misses, windows, locks, and what /akun says about it.

Dates are all relative to today and passed explicitly into apply_penalties, so
nothing here depends on when the suite runs.
"""

from datetime import time, timedelta

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from io import StringIO

from accounts.models import Member
from reminders.models import Reminder
from visits.models import Visit

from .models import (
    BookingPenalty,
    Class,
    ClassInstance,
    ClassMiss,
    ClassSchedule,
    PenaltySettings,
    booking_block_reason,
)
from .penalties import apply_penalties, member_state, miss_days_in_window, record_misses


class PenaltyTestCase(TestCase):
    """Shared fixtures: one member, one class, and helpers to book and attend."""

    def setUp(self):
        self.today = timezone.localdate()
        self.settings = PenaltySettings.get_solo()
        # The seeded row starts from the day the migration ran, which in a test
        # database is today. Every test here books classes in the past.
        self.settings.effective_from = self.today - timedelta(days=365)
        self.settings.enabled = True
        self.settings.window_days = 15
        self.settings.misses_allowed = 2
        self.settings.ban_days = 3
        self.settings.save()

        self.member = self.a_member("penalty@example.com", "628570000001")
        self.class_obj = Class.objects.create(
            name="Kelas Pemula", description="Beginner", max_members=2
        )

    def a_member(self, email, phone, name="Penalty Member"):
        return Member.objects.create(
            name=name,
            email=email,
            phone_number=phone,
            gender="M",
            age=30,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
        )

    def instance_on(self, day, hour=7):
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=self.class_obj,
            day_of_week=day.weekday(),
            start_time=time(hour, 0),
            defaults={"end_time": time(hour + 1, 0)},
        )
        return ClassInstance.objects.create(
            class_schedule=schedule,
            date=day,
            start_time=time(hour, 0),
            end_time=time(hour + 1, 0),
        )

    def book(self, day, hour=7, member=None):
        instance = self.instance_on(day, hour)
        instance.booked_members.add(member or self.member)
        return instance

    def attend(self, day, member=None, hour=19):
        """A check-in on that local day. check_in_time is auto_now_add."""
        visit = Visit.objects.create(member=member or self.member)
        when = timezone.make_aware(
            timezone.datetime.combine(day, time(hour, 30))
        )
        Visit.objects.filter(pk=visit.pk).update(check_in_time=when)
        return visit

    def miss_days(self, count, first_offset=1):
        """Book and skip `count` classes, each on its own day."""
        days = []
        for index in range(count):
            day = self.today - timedelta(days=first_offset + index)
            self.book(day)
            record_misses(day)
            days.append(day)
        return days


class RecordMissesTest(PenaltyTestCase):
    def test_a_booking_with_no_visit_that_day_is_a_miss(self):
        day = self.today - timedelta(days=1)
        self.book(day)

        recorded = record_misses(day)

        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0].class_date, day)
        self.assertEqual(recorded[0].class_name, "Kelas Pemula")

    def test_coming_later_the_same_day_counts_as_attending(self):
        # Booked 07:00, skipped it, came at 19:00. Not a miss: the strict version
        # would punish everyone who forgot to check in on time.
        day = self.today - timedelta(days=1)
        self.book(day, hour=7)
        self.attend(day, hour=19)

        self.assertEqual(record_misses(day), [])

    def test_a_cancelled_class_is_never_a_miss(self):
        day = self.today - timedelta(days=1)
        instance = self.book(day)
        instance.status = "CANCELLED"
        instance.save()

        self.assertEqual(record_misses(day), [])

    def test_being_on_the_waitlist_is_not_a_booking(self):
        day = self.today - timedelta(days=1)
        instance = self.instance_on(day)
        instance.waitlisted_members.add(self.member)

        self.assertEqual(record_misses(day), [])

    def test_running_twice_records_nothing_new(self):
        day = self.today - timedelta(days=1)
        self.book(day)

        record_misses(day)
        second = record_misses(day)

        self.assertEqual(second, [])
        self.assertEqual(ClassMiss.objects.count(), 1)

    def test_classes_before_the_start_date_are_ignored(self):
        self.settings.effective_from = self.today
        self.settings.save()
        day = self.today - timedelta(days=1)
        self.book(day)

        self.assertEqual(record_misses(day), [])
        self.assertEqual(ClassMiss.objects.count(), 0)


class MissWindowTest(PenaltyTestCase):
    def test_two_classes_missed_on_one_day_count_as_one(self):
        day = self.today - timedelta(days=1)
        self.book(day, hour=7)
        self.book(day, hour=18)
        record_misses(day)

        self.assertEqual(ClassMiss.objects.count(), 2)
        self.assertEqual(miss_days_in_window(self.member, self.today), 1)

    def test_misses_older_than_the_window_drop_out(self):
        old = self.today - timedelta(days=20)
        recent = self.today - timedelta(days=2)
        self.book(old)
        self.book(recent)
        record_misses(old)
        record_misses(recent)

        self.assertEqual(miss_days_in_window(self.member, self.today), 1)

    def test_the_window_edge_is_inclusive(self):
        edge = self.today - timedelta(days=14)  # 15 day window counting today
        self.book(edge)
        record_misses(edge)

        self.assertEqual(miss_days_in_window(self.member, self.today), 1)

        beyond = self.today - timedelta(days=15)
        self.book(beyond)
        record_misses(beyond)
        self.assertEqual(miss_days_in_window(self.member, self.today), 1)

    def test_misses_before_the_start_date_never_count(self):
        day = self.today - timedelta(days=3)
        self.book(day)
        record_misses(day)
        self.settings.effective_from = self.today - timedelta(days=1)
        self.settings.save()

        self.assertEqual(miss_days_in_window(self.member, self.today), 0)


class PenaltyTriggerTest(PenaltyTestCase):
    def test_the_allowance_is_free(self):
        self.miss_days(2)
        day = self.today
        self.book(day)  # a third booking, but attended

        self.attend(day)
        apply_penalties(day=day)

        self.assertFalse(BookingPenalty.objects.exists())
        self.member.refresh_from_db()
        self.assertIsNone(self.member.booking_blocked_until)

    def test_the_third_miss_locks_booking_for_three_days(self):
        self.miss_days(2)
        self.book(self.today)

        report = apply_penalties(day=self.today)

        self.assertEqual(len(report["penalties"]), 1)
        penalty = BookingPenalty.objects.get()
        self.assertEqual(penalty.starts_on, self.today)
        self.assertEqual(penalty.blocked_until, self.today + timedelta(days=3))
        self.assertEqual(penalty.miss_days, 3)

        self.member.refresh_from_db()
        self.assertEqual(
            self.member.booking_blocked_until, self.today + timedelta(days=3)
        )
        self.assertTrue(self.member.booking_locked(self.today))
        # The day the lock expires, they can book again.
        self.assertFalse(
            self.member.booking_locked(self.today + timedelta(days=3))
        )

    def test_bookings_inside_the_locked_days_are_cancelled(self):
        self.miss_days(2)
        self.book(self.today)
        tomorrow = self.book(self.today + timedelta(days=1))
        day_after = self.book(self.today + timedelta(days=2))
        after_lock = self.book(self.today + timedelta(days=3))

        apply_penalties(day=self.today)

        self.assertNotIn(self.member, tomorrow.booked_members.all())
        self.assertNotIn(self.member, day_after.booked_members.all())
        # The lock ends on day 3, so that booking survives.
        self.assertIn(self.member, after_lock.booked_members.all())
        self.assertEqual(BookingPenalty.objects.get().bookings_cancelled, 2)

    def test_todays_booking_is_left_alone_as_evidence(self):
        self.miss_days(2)
        today_class = self.book(self.today)

        apply_penalties(day=self.today)

        # Removing it would erase the miss from the admin's no-show report.
        self.assertIn(self.member, today_class.booked_members.all())
        self.assertTrue(
            ClassMiss.objects.filter(class_instance=today_class).exists()
        )

    def test_cancelling_promotes_whoever_is_next_on_the_waitlist(self):
        other = self.a_member("waiting@example.com", "628570000002", "Waiting Member")
        self.miss_days(2)
        self.book(self.today)
        tomorrow = self.book(self.today + timedelta(days=1))
        tomorrow.waitlisted_members.add(other)

        apply_penalties(day=self.today)

        self.assertIn(other, tomorrow.booked_members.all())
        self.assertNotIn(other, tomorrow.waitlisted_members.all())

    def test_waitlist_places_inside_the_lock_are_dropped(self):
        self.miss_days(2)
        self.book(self.today)
        tomorrow = self.instance_on(self.today + timedelta(days=1))
        tomorrow.waitlisted_members.add(self.member)

        apply_penalties(day=self.today)

        self.assertNotIn(self.member, tomorrow.waitlisted_members.all())
        self.assertEqual(BookingPenalty.objects.get().waitlists_cleared, 1)

    def test_staff_get_a_reminder_so_someone_can_explain(self):
        self.miss_days(2)
        self.book(self.today)

        apply_penalties(day=self.today)

        reminder = Reminder.objects.get(reminder_type="PENALTI_KELAS")
        self.assertEqual(reminder.member, self.member)
        self.assertEqual(reminder.due_date, self.today)
        self.assertIn("dikunci", reminder.reason)

    def test_running_twice_in_one_evening_penalises_once(self):
        self.miss_days(2)
        self.book(self.today)

        apply_penalties(day=self.today)
        report = apply_penalties(day=self.today)

        self.assertEqual(BookingPenalty.objects.count(), 1)
        self.assertEqual(report["skipped_existing"], 1)
        self.assertEqual(Reminder.objects.filter(reminder_type="PENALTI_KELAS").count(), 1)

    def test_a_fourth_miss_lands_another_penalty(self):
        self.miss_days(2)
        self.book(self.today)
        apply_penalties(day=self.today)

        # They serve the lock, then miss again on the day it ends.
        later = self.today + timedelta(days=3)
        self.book(later)
        apply_penalties(day=later)

        self.assertEqual(BookingPenalty.objects.count(), 2)
        self.member.refresh_from_db()
        self.assertEqual(self.member.booking_blocked_until, later + timedelta(days=3))

    def test_a_new_penalty_never_shortens_one_already_running(self):
        self.miss_days(2)
        self.book(self.today)
        apply_penalties(day=self.today)

        self.member.refresh_from_db()
        self.member.booking_blocked_until = self.today + timedelta(days=30)
        self.member.save()

        later = self.today + timedelta(days=1)
        self.book(later)
        apply_penalties(day=later)

        self.member.refresh_from_db()
        self.assertEqual(
            self.member.booking_blocked_until, self.today + timedelta(days=30)
        )

    def test_switching_it_off_in_admin_stops_everything(self):
        self.settings.enabled = False
        self.settings.save()
        self.miss_days(2)
        self.book(self.today)

        report = apply_penalties(day=self.today)

        self.assertFalse(report["enabled"])
        self.assertFalse(BookingPenalty.objects.exists())

    def test_settings_are_respected(self):
        self.settings.misses_allowed = 0
        self.settings.ban_days = 7
        self.settings.save()
        self.book(self.today)

        apply_penalties(day=self.today)

        penalty = BookingPenalty.objects.get()
        self.assertEqual(penalty.blocked_until, self.today + timedelta(days=7))

    def test_dry_run_changes_nothing(self):
        self.miss_days(2)
        self.book(self.today)
        tomorrow = self.book(self.today + timedelta(days=1))

        report = apply_penalties(day=self.today, dry_run=True)

        self.assertEqual(len(report["penalties"]), 1)
        self.assertFalse(BookingPenalty.objects.exists())
        self.assertIn(self.member, tomorrow.booked_members.all())
        self.member.refresh_from_db()
        self.assertIsNone(self.member.booking_blocked_until)

    def test_one_members_misses_do_not_touch_another(self):
        other = self.a_member("clean@example.com", "628570000003", "Clean Member")
        self.miss_days(2)
        self.book(self.today)
        self.book(self.today, hour=18, member=other)
        self.attend(self.today, member=other)

        apply_penalties(day=self.today)

        other.refresh_from_db()
        self.assertIsNone(other.booking_blocked_until)
        self.assertEqual(BookingPenalty.objects.count(), 1)


class BookingBlockedTest(PenaltyTestCase):
    def lock(self, days=3):
        self.member.booking_blocked_until = self.today + timedelta(days=days)
        self.member.save()

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_the_block_reason_outranks_everything_else(self):
        self.lock()
        instance = self.instance_on(self.today + timedelta(days=1))

        block = booking_block_reason(self.member, instance)

        self.assertEqual(block["code"], "PENALTY")
        self.assertIn("dikunci", block["message"])

    def test_no_block_once_the_lock_has_expired(self):
        self.member.booking_blocked_until = self.today
        self.member.save()
        instance = self.instance_on(self.today + timedelta(days=1))

        self.assertIsNone(booking_block_reason(self.member, instance))

    def test_clearing_the_field_unlocks_immediately(self):
        self.lock()
        self.member.booking_blocked_until = None
        self.member.save()
        instance = self.instance_on(self.today + timedelta(days=1))

        self.assertIsNone(booking_block_reason(self.member, instance))

    def test_the_class_list_shows_it_and_hides_the_button(self):
        self.lock()
        self.instance_on(self.today + timedelta(days=1))
        self.login()

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Kena Penalti")
        self.assertNotContains(response, "Masuk Antrian")

    def test_the_post_refuses_too(self):
        self.lock()
        instance = self.instance_on(self.today + timedelta(days=1))
        self.login()

        self.client.post(reverse("classes:book_class", args=[instance.id]))

        self.assertNotIn(self.member, instance.booked_members.all())


class AccountCardTest(PenaltyTestCase):
    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_a_member_who_always_turns_up_never_sees_it(self):
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertIsNone(response.context["class_penalty"])
        self.assertNotContains(response, "class-penalty")

    def test_one_miss_shows_the_quiet_history_line(self):
        self.miss_days(1)
        self.login()

        response = self.client.get(reverse("member_details"))
        state = response.context["class_penalty"]

        self.assertEqual(state["level"], "history")
        self.assertEqual(state["misses_in_window"], 1)
        self.assertContains(response, "Catatan tempat kelas yang kebuang")

    def test_the_last_free_strike_is_a_warning(self):
        self.miss_days(2)
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertEqual(response.context["class_penalty"]["level"], "warning")
        self.assertContains(response, "sekali lagi kena penalti")

    def test_a_locked_member_is_told_when_they_can_book_again(self):
        self.miss_days(2)
        self.book(self.today)
        apply_penalties(day=self.today)
        self.login()

        response = self.client.get(reverse("member_details"))
        state = response.context["class_penalty"]

        self.assertEqual(state["level"], "banned")
        self.assertEqual(state["blocked_until"], self.today + timedelta(days=3))
        self.assertContains(response, "Booking kelas dikunci sampai")

    def test_history_survives_the_lock_expiring(self):
        self.miss_days(2)
        self.book(self.today)
        apply_penalties(day=self.today)
        self.member.refresh_from_db()
        self.member.booking_blocked_until = self.today  # expired
        self.member.save()
        self.login()

        state = member_state(self.member, self.today)

        self.assertEqual(state["level"], "history")
        self.assertIsNone(state["blocked_until"])


class CommandTest(PenaltyTestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("apply_class_penalties", *args, stdout=out)
        return out.getvalue()

    def test_it_reports_and_applies(self):
        self.miss_days(2)
        self.book(self.today)

        output = self.run_command()

        self.assertIn("1 penalties applied", output)
        self.assertTrue(BookingPenalty.objects.exists())

    def test_dry_run_says_would_and_saves_nothing(self):
        self.miss_days(2)
        self.book(self.today)

        output = self.run_command("--dry-run")

        self.assertIn("would be applied", output)
        self.assertFalse(BookingPenalty.objects.exists())

    def test_a_skipped_evening_can_be_caught_up(self):
        yesterday = self.today - timedelta(days=1)
        self.miss_days(2, first_offset=2)
        self.book(yesterday)

        self.run_command("--date", yesterday.isoformat())

        penalty = BookingPenalty.objects.get()
        self.assertEqual(penalty.starts_on, yesterday)

    def test_a_bad_date_is_an_error_not_a_traceback(self):
        with self.assertRaises(CommandError):
            self.run_command("--date", "kemarin")

    def test_it_says_so_when_switched_off(self):
        self.settings.enabled = False
        self.settings.save()

        self.assertIn("switched off", self.run_command())


class LateCancelTest(PenaltyTestCase):
    """Cancelling inside the deadline costs the same as not turning up.

    Times here are built from `timezone.now()` rather than a fixed hour, so a
    class "two hours from now" is always two hours from now whenever the suite
    runs, including across midnight.
    """

    def setUp(self):
        super().setUp()
        self.settings.late_cancel_hours = 4
        self.settings.save()

    def login(self, member=None):
        session = self.client.session
        session["member_email"] = (member or self.member).email
        session.save()

    def class_starting_in(self, minutes, member=None):
        """A class starting `minutes` from now, with the member booked into it."""
        start = timezone.localtime(timezone.now()) + timedelta(minutes=minutes)
        start = start.replace(second=0, microsecond=0)
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=self.class_obj,
            day_of_week=start.date().weekday(),
            start_time=start.time(),
            defaults={"end_time": (start + timedelta(hours=1)).time()},
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=start.date(),
            start_time=start.time(),
            end_time=(start + timedelta(hours=1)).time(),
        )
        instance.booked_members.add(member or self.member)
        return instance

    def cancel(self, instance):
        return self.client.post(
            reverse("classes:cancel_class", args=[instance.id]), follow=True
        )

    def test_cancelling_early_costs_nothing(self):
        instance = self.class_starting_in(60 * 6)
        self.login()

        response = self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 0)
        self.assertNotIn(self.member, instance.booked_members.all())
        self.assertContains(response, "Makasih udah batalin")

    def test_cancelling_inside_the_deadline_is_a_strike(self):
        instance = self.class_starting_in(120)
        self.login()

        response = self.cancel(instance)

        miss = ClassMiss.objects.get(member=self.member)
        self.assertEqual(miss.kind, "LATE_CANCEL")
        self.assertEqual(miss.class_date, instance.date)
        self.assertNotIn(self.member, instance.booked_members.all())
        self.assertContains(response, "dihitung 1 kali buang tempat")

    def test_the_deadline_is_exactly_the_configured_hours(self):
        """Four hours and one minute out is still free; three hours is not."""
        early = self.class_starting_in(60 * 4 + 1)
        late = self.class_starting_in(60 * 3)
        self.login()

        self.cancel(early)
        self.assertEqual(ClassMiss.objects.count(), 0)

        self.cancel(late)
        self.assertEqual(ClassMiss.objects.count(), 1)

    def test_leaving_the_waitlist_late_is_never_a_strike(self):
        """A waitlist place is not a seat, so dropping it costs nobody one."""
        instance = self.class_starting_in(30, member=self.a_member(
            "holder@example.com", "628570000091"
        ))
        instance.waitlisted_members.add(self.member)
        self.login()

        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 0)
        self.assertNotIn(self.member, instance.waitlisted_members.all())

    def test_a_seat_handed_over_after_the_deadline_carries_no_strike(self):
        """Promoted 30 minutes before, with no way to be told. Not their fault."""
        other = self.a_member("dropper@example.com", "628570000092")
        instance = self.class_starting_in(30, member=other)
        instance.waitlisted_members.add(self.member)
        instance.booked_members.remove(other)
        instance.move_from_waitlist()
        self.assertIn(self.member, instance.booked_members.all())

        self.login()
        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 0)

    def test_a_seat_handed_over_before_the_deadline_still_counts(self):
        """Promoted with a day to notice, so the ordinary rule applies."""
        other = self.a_member("dropper2@example.com", "628570000093")
        instance = self.class_starting_in(120, member=other)
        instance.waitlisted_members.add(self.member)
        instance.booked_members.remove(other)
        instance.move_from_waitlist()

        promotion = self.member.waitlist_promotions.get(class_instance=instance)
        promotion.promoted_at = timezone.now() - timedelta(days=1)
        promotion.save()

        self.login()
        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 1)

    def test_a_class_the_gym_cancelled_is_not_the_members_fault(self):
        instance = self.class_starting_in(60)
        instance.status = "CANCELLED"
        instance.save()
        self.login()

        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 0)

    def test_nothing_is_recorded_while_the_penalty_is_switched_off(self):
        self.settings.enabled = False
        self.settings.save()
        instance = self.class_starting_in(60)
        self.login()

        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 0)

    def test_a_late_cancel_counts_towards_the_ban(self):
        """Two ordinary misses plus one late cancel tips a member over."""
        self.miss_days(2)
        instance = self.class_starting_in(60)
        self.login()

        self.cancel(instance)
        apply_penalties(day=instance.date)

        self.member.refresh_from_db()
        self.assertTrue(self.member.booking_locked())
        self.assertEqual(
            BookingPenalty.objects.get(member=self.member).miss_days, 3
        )

    def test_a_late_cancel_and_a_no_show_on_one_day_is_one_strike(self):
        """Strikes are per day, whichever way the seats were wasted."""
        cancelled = self.class_starting_in(60)
        skipped = self.class_starting_in(90)
        skipped.booked_members.add(self.member)
        self.login()

        self.cancel(cancelled)
        record_misses(cancelled.date)

        self.assertEqual(miss_days_in_window(self.member, cancelled.date), 1)

    def test_cancelling_twice_cannot_double_count(self):
        """Re-booking and cancelling the same class again is still one seat."""
        instance = self.class_starting_in(60)
        self.login()

        self.cancel(instance)
        instance.booked_members.add(self.member)
        self.cancel(instance)

        self.assertEqual(ClassMiss.objects.count(), 1)

    def test_the_account_page_shows_which_kind_it_was(self):
        instance = self.class_starting_in(60)
        self.login()
        self.cancel(instance)

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "batalin mepet")


class PendingLockTest(PenaltyTestCase):
    """The hours between going over the allowance and the nightly run.

    Only reachable since late cancellations are recorded live: a member can be
    three strikes deep at four in the afternoon while the lock does not land
    until nine. Saying nothing during those hours is how a member ends up
    booking two more classes and losing them overnight.
    """

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_over_the_allowance_but_not_yet_locked_says_so(self):
        self.miss_days(3)
        self.login()

        response = self.client.get(reverse("member_details"))
        state = response.context["class_penalty"]

        self.assertEqual(state["level"], "pending")
        self.assertContains(response, "Nanti malam booking kelas kamu dikunci")

    def test_the_lock_itself_still_wins(self):
        self.miss_days(3)
        apply_penalties(day=self.today - timedelta(days=1))
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertEqual(response.context["class_penalty"]["level"], "banned")

    def test_a_member_inside_the_allowance_is_unaffected(self):
        self.miss_days(1)
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertEqual(response.context["class_penalty"]["level"], "history")

    def test_a_lock_already_served_for_those_misses_is_not_pending(self):
        """Over the allowance, but they already did the three days for it."""
        self.miss_days(2)
        self.book(self.today)
        apply_penalties(day=self.today)
        self.member.refresh_from_db()
        self.member.booking_blocked_until = self.today  # expired this morning
        self.member.save()
        self.login()

        state = member_state(self.member, self.today)

        self.assertEqual(state["level"], "history")

    def test_a_fresh_miss_after_an_old_lock_is_pending_again(self):
        self.miss_days(2)
        self.book(self.today - timedelta(days=4))
        apply_penalties(day=self.today - timedelta(days=4))
        self.member.refresh_from_db()
        self.member.booking_blocked_until = self.today
        self.member.save()

        # A new miss today, which tonight's run has not seen
        self.book(self.today)
        record_misses(self.today)
        self.login()

        state = member_state(self.member, self.today)

        self.assertEqual(state["level"], "pending")
