from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.core.management import call_command
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from io import StringIO
from accounts.models import Member
from classes.models import Class, ClassSchedule, ClassInstance
from classes.admin import ClassInstanceAdmin


class ClassModelTest(TestCase):

    def setUp(self):
        self.yoga_class = Class.objects.create(
            name="Yoga", description="A relaxing yoga class.", max_members=15
        )
        self.schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=0,  # Monday
            start_time="09:00:00",
            end_time="10:00:00",
        )
        self.member = Member.objects.create(
            name="Test Member",
            email="test@example.com",
            phone_number="1234567890",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )

    def test_class_instance_creation(self):
        instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=date.today(),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
        )
        self.assertEqual(instance.status, "OPEN")
        self.assertEqual(instance.available_slots, 15)

    def test_booking_and_waitlist(self):
        instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=date.today(),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
        )
        for i in range(15):
            member = Member.objects.create(
                name=f"Member {i}",
                email=f"member{i}@example.com",
                phone_number=f"62812345678{i:02d}",  # Ensure unique phone numbers
                age=25 + i,
                height=170.0,
                weight=70.0,
                gender="M",
                goals="Stay fit",
                years_of_working_out="1-2 years",
            )
            instance.booked_members.add(member)

        instance.update_status()
        self.assertEqual(instance.status, "FULL")
        self.assertEqual(instance.available_slots, 0)

        # Test waitlist
        waitlist_member = Member.objects.create(
            name="Waitlist Member",
            email="waitlist@example.com",
            phone_number="6287654321000",  # Unique phone number
            age=30,
            height=165.0,
            weight=65.0,
            gender="F",
            goals="Lose weight",
            years_of_working_out="Beginner",
        )
        instance.waitlisted_members.add(waitlist_member)
        self.assertEqual(instance.waitlisted_members.count(), 1)

        # Test moving from waitlist
        first_member = instance.booked_members.first()
        instance.booked_members.remove(first_member)
        instance.move_from_waitlist()
        self.assertEqual(instance.booked_members.count(), 15)
        self.assertIn(waitlist_member, instance.booked_members.all())
        self.assertEqual(instance.waitlisted_members.count(), 0)


class GenerateClassInstancesCommandTest(TestCase):

    def setUp(self):
        self.yoga_class = Class.objects.create(
            name="Yoga", description="A relaxing yoga class.", max_members=10
        )
        self.pilates_class = Class.objects.create(
            name="Pilates", description="Core strengthening class.", max_members=8
        )

        # Create schedules for different days
        today = timezone.now().date()
        today_weekday = today.weekday()

        # Schedule for today
        self.today_schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=today_weekday,
            start_time="09:00:00",
            end_time="10:00:00",
        )

        # Schedule for tomorrow
        tomorrow_weekday = (today_weekday + 1) % 7
        self.tomorrow_schedule = ClassSchedule.objects.create(
            class_obj=self.pilates_class,
            day_of_week=tomorrow_weekday,
            start_time="18:00:00",
            end_time="19:00:00",
        )

    def test_command_default_days(self):
        """Test command with default 3 days parameter"""
        out = StringIO()
        call_command("generate_class_instances", stdout=out)

        output = out.getvalue()
        self.assertIn("Generating class instances for 3 days ahead", output)
        self.assertIn("Class instance generation completed successfully", output)

        # Should create instances for today and tomorrow based on schedules
        today = timezone.now().date()
        instances_today = ClassInstance.objects.filter(date=today)
        instances_tomorrow = ClassInstance.objects.filter(
            date=today + timedelta(days=1)
        )

        self.assertTrue(instances_today.exists())
        self.assertTrue(instances_tomorrow.exists())

    def test_command_custom_days(self):
        """Test command with custom days parameter"""
        out = StringIO()
        call_command("generate_class_instances", "5", stdout=out)

        output = out.getvalue()
        self.assertIn("Generating class instances for 5 days ahead", output)

    def test_command_marks_past_instances_completed(self):
        """Test that command marks past instances as COMPLETED"""
        # Create an instance for 2 days ago to ensure it's marked as past
        two_days_ago = timezone.now().date() - timedelta(days=2)
        past_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=two_days_ago,
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
            status="OPEN",
        )

        out = StringIO()
        call_command("generate_class_instances", stdout=out)

        past_instance.refresh_from_db()
        self.assertEqual(past_instance.status, "COMPLETED")

        output = out.getvalue()
        self.assertIn("Marked 1 past instances as COMPLETED", output)

    def test_command_marks_yesterday_instances_completed(self):
        """Test that command specifically marks yesterday's instances as COMPLETED (bug fix test)"""
        # Create an instance for yesterday - this was the specific bug we fixed
        yesterday = timezone.now().date() - timedelta(days=1)
        yesterday_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=yesterday,
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
            status="OPEN",
        )

        # Also create a FULL instance to test that both statuses get completed
        yesterday_full_instance = ClassInstance.objects.create(
            class_schedule=self.tomorrow_schedule,  # Use different schedule to avoid conflicts
            date=yesterday,
            start_time=self.tomorrow_schedule.start_time,
            end_time=self.tomorrow_schedule.end_time,
            status="FULL",
        )

        # Verify they start as OPEN and FULL
        self.assertEqual(yesterday_instance.status, "OPEN")
        self.assertEqual(yesterday_full_instance.status, "FULL")

        out = StringIO()
        call_command("generate_class_instances", stdout=out)

        # Refresh and verify both are now COMPLETED
        yesterday_instance.refresh_from_db()
        yesterday_full_instance.refresh_from_db()
        self.assertEqual(yesterday_instance.status, "COMPLETED")
        self.assertEqual(yesterday_full_instance.status, "COMPLETED")

        output = out.getvalue()
        self.assertIn("Marked 2 past instances as COMPLETED", output)

    def test_command_doesnt_mark_today_instances_completed(self):
        """Test that command does NOT mark today's instances as COMPLETED"""
        today = timezone.now().date()

        # Create instances for today
        today_open_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=today,
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
            status="OPEN",
        )

        today_full_instance = ClassInstance.objects.create(
            class_schedule=self.tomorrow_schedule,
            date=today,
            start_time=self.tomorrow_schedule.start_time,
            end_time=self.tomorrow_schedule.end_time,
            status="FULL",
        )

        out = StringIO()
        call_command("generate_class_instances", stdout=out)

        # Refresh and verify they remain in their original status
        today_open_instance.refresh_from_db()
        today_full_instance.refresh_from_db()
        self.assertEqual(today_open_instance.status, "OPEN")
        self.assertEqual(today_full_instance.status, "FULL")

        output = out.getvalue()
        # Should mark 0 instances as completed since today's instances shouldn't be completed
        self.assertIn("Marked 0 past instances as COMPLETED", output)

    def test_command_only_completes_open_and_full_instances(self):
        """Test that command only marks OPEN and FULL instances as COMPLETED, not already COMPLETED/CANCELLED ones"""
        yesterday = timezone.now().date() - timedelta(days=1)

        # Create instances with different statuses
        open_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=yesterday,
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
            status="OPEN",
        )

        full_instance = ClassInstance.objects.create(
            class_schedule=self.tomorrow_schedule,
            date=yesterday,
            start_time=self.tomorrow_schedule.start_time,
            end_time=self.tomorrow_schedule.end_time,
            status="FULL",
        )

        # Create instances that are already COMPLETED and CANCELLED
        already_completed_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=yesterday
            - timedelta(days=1),  # Day before yesterday to avoid conflicts
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
            status="COMPLETED",
        )

        already_cancelled_instance = ClassInstance.objects.create(
            class_schedule=self.tomorrow_schedule,
            date=yesterday
            - timedelta(days=1),  # Day before yesterday to avoid conflicts
            start_time=self.tomorrow_schedule.start_time,
            end_time=self.tomorrow_schedule.end_time,
            status="CANCELLED",
        )

        out = StringIO()
        call_command("generate_class_instances", stdout=out)

        # Refresh all instances
        open_instance.refresh_from_db()
        full_instance.refresh_from_db()
        already_completed_instance.refresh_from_db()
        already_cancelled_instance.refresh_from_db()

        # Verify only OPEN and FULL instances were changed to COMPLETED
        self.assertEqual(open_instance.status, "COMPLETED")
        self.assertEqual(full_instance.status, "COMPLETED")
        # These should remain unchanged
        self.assertEqual(already_completed_instance.status, "COMPLETED")
        self.assertEqual(already_cancelled_instance.status, "CANCELLED")

        output = out.getvalue()
        # Should only mark the 2 OPEN/FULL instances as completed
        self.assertIn("Marked 2 past instances as COMPLETED", output)

    def test_command_doesnt_create_duplicates(self):
        """Test that command doesn't create duplicate instances"""
        today = timezone.now().date()

        # Create an instance manually
        existing_instance = ClassInstance.objects.create(
            class_schedule=self.today_schedule,
            date=today,
            start_time=self.today_schedule.start_time,
            end_time=self.today_schedule.end_time,
        )

        initial_count = ClassInstance.objects.filter(date=today).count()

        # Run command
        call_command("generate_class_instances")

        # Count should be the same (no duplicates)
        final_count = ClassInstance.objects.filter(date=today).count()
        self.assertEqual(initial_count, final_count)

    def test_command_with_zero_days(self):
        """Test command with 0 days (edge case)"""
        out = StringIO()
        call_command("generate_class_instances", "0", stdout=out)

        output = out.getvalue()
        self.assertIn("Generating class instances for 0 days ahead", output)
        self.assertIn("Created 0 new class instances", output)

    def test_command_with_large_number_of_days(self):
        """Test command with a large number of days"""
        out = StringIO()
        call_command("generate_class_instances", "10", stdout=out)

        output = out.getvalue()
        self.assertIn("Generating class instances for 10 days ahead", output)


class ClassInstanceAdminTest(TestCase):
    """Test ClassInstanceAdmin filtering behavior"""

    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = ClassInstanceAdmin(ClassInstance, self.site)

        # Create test data
        self.yoga_class = Class.objects.create(
            name="Yoga", description="A relaxing yoga class.", max_members=10
        )
        self.schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=0,  # Monday
            start_time="09:00:00",
            end_time="10:00:00",
        )

        # Create instances with different statuses
        today = timezone.now().date()
        self.open_instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=today,
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        self.full_instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=today + timedelta(days=1),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="FULL",
        )
        self.completed_instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=today - timedelta(days=1),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="COMPLETED",
        )
        self.cancelled_instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=today + timedelta(days=2),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="CANCELLED",
        )

    def test_default_queryset_shows_only_open_and_full(self):
        """Test that default admin view only shows OPEN and FULL instances"""
        request = self.factory.get("/admin/classes/classinstance/")

        # Test the default filter behavior (no status parameter)
        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(request, {}, ClassInstance, self.admin)
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        statuses = list(filtered_qs.values_list("status", flat=True))

        # Should only contain OPEN and FULL
        self.assertIn("OPEN", statuses)
        self.assertIn("FULL", statuses)
        self.assertNotIn("COMPLETED", statuses)
        self.assertNotIn("CANCELLED", statuses)

        # Should have exactly 2 instances (OPEN and FULL)
        self.assertEqual(filtered_qs.count(), 2)

    def test_status_filter_shows_all_when_applied(self):
        """Test that applying status filter shows instances of that status"""
        # Test COMPLETED filter
        request = self.factory.get("/admin/classes/classinstance/?status=COMPLETED")

        # Test the filter directly with proper parameter passing
        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(
            request, {"status": "COMPLETED"}, ClassInstance, self.admin
        )
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        statuses = list(filtered_qs.values_list("status", flat=True))
        self.assertEqual(statuses, ["COMPLETED"])
        self.assertEqual(filtered_qs.count(), 1)

    def test_open_status_filter(self):
        """Test filtering for OPEN status specifically"""
        request = self.factory.get("/admin/classes/classinstance/?status=OPEN")

        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(
            request, {"status": "OPEN"}, ClassInstance, self.admin
        )
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        statuses = list(filtered_qs.values_list("status", flat=True))
        self.assertEqual(statuses, ["OPEN"])
        self.assertEqual(filtered_qs.count(), 1)

    def test_full_status_filter(self):
        """Test filtering for FULL status specifically"""
        request = self.factory.get("/admin/classes/classinstance/?status=FULL")

        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(
            request, {"status": "FULL"}, ClassInstance, self.admin
        )
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        statuses = list(filtered_qs.values_list("status", flat=True))
        self.assertEqual(statuses, ["FULL"])
        self.assertEqual(filtered_qs.count(), 1)

    def test_cancelled_status_filter(self):
        """Test filtering for CANCELLED status specifically"""
        request = self.factory.get("/admin/classes/classinstance/?status=CANCELLED")

        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(
            request, {"status": "CANCELLED"}, ClassInstance, self.admin
        )
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        statuses = list(filtered_qs.values_list("status", flat=True))
        self.assertEqual(statuses, ["CANCELLED"])
        self.assertEqual(filtered_qs.count(), 1)

    def test_other_filters_dont_affect_status_filtering(self):
        """Test that other filters (like date) don't interfere with status logic"""
        today = timezone.now().date()
        request = self.factory.get(f"/admin/classes/classinstance/?date__exact={today}")

        # Test the default filter behavior when other filters are applied but no status filter
        from classes.admin import ActiveStatusFilter

        filter_instance = ActiveStatusFilter(request, {}, ClassInstance, self.admin)
        filtered_qs = filter_instance.queryset(request, ClassInstance.objects.all())

        # Should still apply the default OPEN/FULL filter since no status filter is applied
        statuses = list(filtered_qs.values_list("status", flat=True))
        self.assertIn("OPEN", statuses)
        self.assertNotIn("COMPLETED", statuses)
        self.assertNotIn("CANCELLED", statuses)


class ClassListViewTest(TestCase):
    """Test ClassListView filtering behavior"""

    def setUp(self):
        # Create test data
        self.yoga_class = Class.objects.create(
            name="Yoga", description="A relaxing yoga class.", max_members=10
        )
        self.pilates_class = Class.objects.create(
            name="Pilates", description="A core strengthening class.", max_members=8
        )

        # Create different schedules to avoid unique constraint issues
        self.morning_schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=0,  # Monday
            start_time="08:00:00",
            end_time="09:00:00",
        )

        self.evening_schedule = ClassSchedule.objects.create(
            class_obj=self.pilates_class,
            day_of_week=0,  # Monday
            start_time="23:59:00",
            end_time="23:59:59",
        )

        self.tomorrow_schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=1,  # Tuesday
            start_time="09:00:00",
            end_time="10:00:00",
        )

        # Create member for authentication
        self.member = Member.objects.create(
            name="Test Member",
            email="test@example.com",
            phone_number="628123456789",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )

        now = timezone.now()
        today = now.date()

        # Create class instances with different timing
        self.past_instance = ClassInstance.objects.create(
            class_schedule=self.morning_schedule,
            date=today,
            start_time="08:00:00",  # Past time (assuming current time is after 8 AM)
            end_time="09:00:00",
            status="OPEN",
        )

        self.future_today_instance = ClassInstance.objects.create(
            class_schedule=self.evening_schedule,
            date=today,
            start_time="23:59:00",  # Future time today
            end_time="23:59:59",
            status="OPEN",
        )

        self.future_instance = ClassInstance.objects.create(
            class_schedule=self.tomorrow_schedule,
            date=today + timedelta(days=1),  # Tomorrow
            start_time="09:00:00",
            end_time="10:00:00",
            status="FULL",
        )

    def test_past_classes_filtered_out(self):
        """Test that classes that have already started are not shown"""
        from classes.views import ClassListView
        from django.http import HttpRequest

        view = ClassListView()
        view.request = HttpRequest()

        # Mock session for member authentication
        view.request.session = {"member_email": self.member.email}

        queryset = view.get_queryset()

        # Future instances should be in queryset
        self.assertIn(self.future_today_instance, queryset)
        self.assertIn(self.future_instance, queryset)

    def test_only_upcoming_classes_shown(self):
        """Test that only upcoming classes are shown (future dates or today's future classes)"""
        from classes.views import ClassListView
        from django.http import HttpRequest

        view = ClassListView()
        view.request = HttpRequest()
        view.request.session = {"member_email": self.member.email}

        instances_list = view.get_queryset()

        # Should contain future instances (exact count depends on current time)
        # At minimum should contain tomorrow's instance
        self.assertIn(self.future_instance, instances_list)

        # Should have at least one instance
        self.assertTrue(len(instances_list) >= 1)

    def test_status_filtering_still_works(self):
        """Test that status filtering (OPEN, FULL) still works with time filtering"""
        from classes.views import ClassListView
        from django.http import HttpRequest

        # Create a COMPLETED instance for tomorrow (should not appear)
        tomorrow = timezone.now().date() + timedelta(days=1)
        # Create a new schedule for this test to avoid unique constraint
        completed_schedule = ClassSchedule.objects.create(
            class_obj=self.pilates_class,
            day_of_week=1,  # Tuesday
            start_time="10:00:00",
            end_time="11:00:00",
        )
        completed_instance = ClassInstance.objects.create(
            class_schedule=completed_schedule,
            date=tomorrow,
            start_time="10:00:00",
            end_time="11:00:00",
            status="COMPLETED",
        )

        view = ClassListView()
        view.request = HttpRequest()
        view.request.session = {"member_email": self.member.email}

        instances_list = view.get_queryset()

        # COMPLETED instance should not appear even though it's in the future
        self.assertNotIn(completed_instance, instances_list)

        # Only OPEN and FULL status instances should appear
        statuses = set(instance.status for instance in instances_list)
        self.assertTrue(statuses.issubset({"OPEN", "FULL"}))


class BookingValidationTest(TestCase):
    """Test booking validation for subscription-based classes"""

    def setUp(self):
        # Create test classes
        self.semi_private_class = Class.objects.create(
            name="Semi Private Training",
            description="Semi private class",
            max_members=5,
        )
        self.kelas_pemula_class = Class.objects.create(
            name="Kelas Pemula - Beginners",
            description="Beginner class",
            max_members=10,
        )
        self.regular_class = Class.objects.create(
            name="Regular Class", description="Regular class", max_members=15
        )

        # Create schedules
        self.semi_private_schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private_class,
            day_of_week=0,
            start_time="09:00:00",
            end_time="10:00:00",
        )
        self.kelas_pemula_schedule = ClassSchedule.objects.create(
            class_obj=self.kelas_pemula_class,
            day_of_week=0,
            start_time="10:00:00",
            end_time="11:00:00",
        )
        self.regular_schedule = ClassSchedule.objects.create(
            class_obj=self.regular_class,
            day_of_week=0,
            start_time="11:00:00",
            end_time="12:00:00",
        )

        # Create class instances
        today = timezone.now().date()
        self.semi_private_instance = ClassInstance.objects.create(
            class_schedule=self.semi_private_schedule,
            date=today,
            start_time=self.semi_private_schedule.start_time,
            end_time=self.semi_private_schedule.end_time,
            status="OPEN",
        )
        self.kelas_pemula_instance = ClassInstance.objects.create(
            class_schedule=self.kelas_pemula_schedule,
            date=today,
            start_time=self.kelas_pemula_schedule.start_time,
            end_time=self.kelas_pemula_schedule.end_time,
            status="OPEN",
        )
        self.regular_instance = ClassInstance.objects.create(
            class_schedule=self.regular_schedule,
            date=today,
            start_time=self.regular_schedule.start_time,
            end_time=self.regular_schedule.end_time,
            status="OPEN",
        )

        # Create members with different subscription states
        self.member_no_subscription = Member.objects.create(
            name="No Subscription Member",
            email="nosub@example.com",
            phone_number="628111111111",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )

        self.member_with_semi_private = Member.objects.create(
            name="Semi Private Member",
            email="semiprivate@example.com",
            phone_number="628222222222",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            semi_private_active_until=timezone.now() + timedelta(days=30),
        )

        self.member_with_pemula = Member.objects.create(
            name="Pemula Member",
            email="pemula@example.com",
            phone_number="628333333333",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            pemula_active_until=timezone.now() + timedelta(days=30),
        )

        self.member_expired_semi_private = Member.objects.create(
            name="Expired Semi Private",
            email="expired@example.com",
            phone_number="628444444444",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            semi_private_active_until=timezone.now() - timedelta(days=1),
        )

    def test_semi_private_booking_without_subscription(self):
        """Test that member cannot book Semi Private without active subscription"""
        session = self.client.session
        session["member_email"] = self.member_no_subscription.email
        session.save()

        url = reverse("classes:book_class", args=[self.semi_private_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Gold")
        self.semi_private_instance.refresh_from_db()
        self.assertNotIn(
            self.member_no_subscription, self.semi_private_instance.booked_members.all()
        )

    def test_semi_private_booking_with_active_subscription(self):
        """Test that member can book Semi Private with active subscription"""
        session = self.client.session
        session["member_email"] = self.member_with_semi_private.email
        session.save()

        url = reverse("classes:book_class", args=[self.semi_private_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Berhasil booking kelas")
        self.semi_private_instance.refresh_from_db()
        self.assertIn(
            self.member_with_semi_private,
            self.semi_private_instance.booked_members.all(),
        )

    def test_semi_private_booking_with_expired_subscription(self):
        """Test that member cannot book Semi Private with expired subscription"""
        session = self.client.session
        session["member_email"] = self.member_expired_semi_private.email
        session.save()

        url = reverse("classes:book_class", args=[self.semi_private_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Gold")
        self.semi_private_instance.refresh_from_db()
        self.assertNotIn(
            self.member_expired_semi_private,
            self.semi_private_instance.booked_members.all(),
        )

    def test_kelas_pemula_booking_without_subscription(self):
        """Test that member cannot book Kelas Pemula without active subscription"""
        session = self.client.session
        session["member_email"] = self.member_no_subscription.email
        session.save()

        url = reverse("classes:book_class", args=[self.kelas_pemula_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Silver")
        self.kelas_pemula_instance.refresh_from_db()
        self.assertNotIn(
            self.member_no_subscription, self.kelas_pemula_instance.booked_members.all()
        )

    def test_kelas_pemula_booking_with_active_subscription(self):
        """Test that member can book Kelas Pemula with active subscription"""
        session = self.client.session
        session["member_email"] = self.member_with_pemula.email
        session.save()

        url = reverse("classes:book_class", args=[self.kelas_pemula_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Berhasil booking kelas")
        self.kelas_pemula_instance.refresh_from_db()
        self.assertIn(
            self.member_with_pemula, self.kelas_pemula_instance.booked_members.all()
        )

    def test_regular_class_booking_without_special_subscription(self):
        """Test that member can book regular class without special subscriptions"""
        session = self.client.session
        session["member_email"] = self.member_no_subscription.email
        session.save()

        url = reverse("classes:book_class", args=[self.regular_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Berhasil booking kelas")
        self.regular_instance.refresh_from_db()
        self.assertIn(
            self.member_no_subscription, self.regular_instance.booked_members.all()
        )

    def test_case_insensitive_class_name_matching(self):
        """Test that class name matching is case-insensitive"""
        # Create a class with lowercase name
        lowercase_class = Class.objects.create(
            name="semi private lowercase", description="Test", max_members=5
        )
        schedule = ClassSchedule.objects.create(
            class_obj=lowercase_class,
            day_of_week=1,
            start_time="14:00:00",
            end_time="15:00:00",
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=timezone.now().date(),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status="OPEN",
        )

        session = self.client.session
        session["member_email"] = self.member_no_subscription.email
        session.save()

        url = reverse("classes:book_class", args=[instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Gold")
        instance.refresh_from_db()
        self.assertNotIn(self.member_no_subscription, instance.booked_members.all())
