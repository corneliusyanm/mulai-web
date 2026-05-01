"""Tests for Class No-Show Tracker admin analytics."""
import csv
from datetime import datetime, time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Member
from classes.models import Class, ClassInstance, ClassSchedule
from visits.admin import compute_class_no_show_data
from visits.models import Visit

User = get_user_model()


class ClassNoShowTrackerTest(TestCase):
    """Behavior tests for no-show detection and admin reporting."""

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.regular_user = User.objects.create_user(
            "user", "user@example.com", "password"
        )

        self.gym_class = Class.objects.create(
            name="Kelas Pemula",
            description="Beginner",
            max_members=10,
        )
        self.schedule = ClassSchedule.objects.create(
            class_obj=self.gym_class,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        self.schedule_afternoon = ClassSchedule.objects.create(
            class_obj=self.gym_class,
            day_of_week=1,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

    def _member(self, name, phone_suffix):
        return Member.objects.create(
            name=name,
            email=f"{name.lower().replace(' ', '')}@example.com",
            phone_number=f"6281234567{phone_suffix}",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1",
            goals="Test",
            know_mulai_gym_from="test",
        )

    def _past_date(self, days_ago=3):
        return timezone.localdate() - timedelta(days=days_ago)

    def test_no_show_when_no_visit_same_day(self):
        class_day = self._past_date()
        m = self._member("No Visit Member", "801")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.booked_members.add(m)

        data = compute_class_no_show_data(class_day, class_day, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 1)
        self.assertEqual(data["rows"][0]["member_name"], "No Visit Member")

    def test_visit_same_day_not_no_show(self):
        class_day = self._past_date()
        m = self._member("Visited Member", "802")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.booked_members.add(m)

        visit = Visit.objects.create(member=m)
        Visit.objects.filter(pk=visit.pk).update(
            check_in_time=timezone.make_aware(
                datetime.combine(class_day, time(8, 30)),
                timezone.get_current_timezone(),
            )
        )

        data = compute_class_no_show_data(class_day, class_day, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 0)
        self.assertEqual(len(data["rows"]), 0)

    def test_waitlist_only_excluded(self):
        class_day = self._past_date()
        wait_member = self._member("Wait Only", "803")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.waitlisted_members.add(wait_member)

        data = compute_class_no_show_data(class_day, class_day, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 0)

    def test_cancelled_instance_excluded_from_table_and_denominator(self):
        class_day = self._past_date()
        m = self._member("Cancelled Class Member", "804")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="CANCELLED",
        )
        inst.booked_members.add(m)

        data = compute_class_no_show_data(class_day, class_day, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 0)
        self.assertEqual(data["confirmed_bookings_past"], 0)

    def test_booking_outside_date_range_excluded(self):
        class_day = self._past_date(10)
        window_end = class_day - timedelta(days=1)
        window_start = window_end - timedelta(days=7)
        m = self._member("Outside Range", "805")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.booked_members.add(m)

        data = compute_class_no_show_data(window_start, window_end, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 0)

    def test_no_show_rate_fixture(self):
        d = self._past_date(5)
        a = self._member("Rate A", "901")
        b = self._member("Rate B", "902")
        c = self._member("Rate C", "903")

        i1 = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=d,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        i1.booked_members.add(a, b)

        i2 = ClassInstance.objects.create(
            class_schedule=self.schedule_afternoon,
            date=d,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status="OPEN",
        )
        i2.booked_members.add(c)

        visit = Visit.objects.create(member=a)
        Visit.objects.filter(pk=visit.pk).update(
            check_in_time=timezone.make_aware(
                datetime.combine(d, time(8, 0)),
                timezone.get_current_timezone(),
            )
        )

        data = compute_class_no_show_data(d, d, today=timezone.localdate())
        self.assertEqual(data["confirmed_bookings_past"], 3)
        self.assertEqual(data["total_no_shows"], 2)
        self.assertAlmostEqual(data["no_show_rate"], (2 / 3) * 100, places=5)

    def test_member_no_show_count_in_range(self):
        d1 = self._past_date(8)
        d2 = self._past_date(7)
        m = self._member("Repeat NoShow", "904")

        for day in (d1, d2):
            inst = ClassInstance.objects.create(
                class_schedule=self.schedule,
                date=day,
                start_time=self.schedule.start_time,
                end_time=self.schedule.end_time,
                status="OPEN",
            )
            inst.booked_members.add(m)

        data = compute_class_no_show_data(d1, d2, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 2)
        counts = {row["no_show_count_in_range"] for row in data["rows"]}
        self.assertEqual(counts, {2})

    def test_future_class_not_listed_as_no_show(self):
        future_day = timezone.localdate() + timedelta(days=14)
        m = self._member("Future Booker", "905")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=future_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.booked_members.add(m)

        data = compute_class_no_show_data(future_day, future_day, today=timezone.localdate())
        self.assertEqual(data["total_no_shows"], 0)
        self.assertEqual(data["confirmed_bookings_past"], 0)

    def test_csv_export_columns_and_rows(self):
        class_day = self._past_date(2)
        m = self._member("CSV Member", "806")
        inst = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=class_day,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        inst.booked_members.add(m)

        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("admin:class-no-shows"),
            {
                "start_date": class_day.isoformat(),
                "end_date": class_day.isoformat(),
                "export": "csv",
            },
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        self.assertEqual(
            rows[0],
            [
                "Class name",
                "Class date",
                "Class start time",
                "Member name",
                "Phone",
                "WhatsApp URL",
                "Member no-show count (range)",
            ],
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "Kelas Pemula")
        self.assertEqual(rows[1][3], "CSV Member")

    def test_page_requires_staff(self):
        class_day = self._past_date(1)
        self.client.login(username="user", password="password")
        response = self.client.get(
            reverse("admin:class-no-shows"),
            {
                "start_date": class_day.isoformat(),
                "end_date": class_day.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_page(self):
        class_day = self._past_date(1)
        self.client.login(username="admin", password="password")
        response = self.client.get(
            reverse("admin:class-no-shows"),
            {
                "start_date": class_day.isoformat(),
                "end_date": class_day.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Class No-Show Tracker")
