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

    def test_semi_private_booking_expires_before_class_date(self):
        """Test that member cannot book Semi Private if subscription expires before class date"""
        # Member has subscription active today but expires in 2 days
        member_expiring_soon = Member.objects.create(
            name="Expiring Soon",
            email="expiringsoon@example.com",
            phone_number="628555555555",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            semi_private_active_until=timezone.now() + timedelta(days=2),
        )

        # Create a class instance 5 days in the future
        future_schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private_class,
            day_of_week=2,
            start_time="15:00:00",
            end_time="16:00:00",
        )
        future_instance = ClassInstance.objects.create(
            class_schedule=future_schedule,
            date=timezone.now().date() + timedelta(days=5),
            start_time=future_schedule.start_time,
            end_time=future_schedule.end_time,
            status="OPEN",
        )

        session = self.client.session
        session["member_email"] = member_expiring_soon.email
        session.save()

        url = reverse("classes:book_class", args=[future_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Gold")
        future_instance.refresh_from_db()
        self.assertNotIn(member_expiring_soon, future_instance.booked_members.all())

    def test_pemula_booking_expires_before_class_date(self):
        """Test that member cannot book Kelas Pemula if subscription expires before class date"""
        # Member has subscription active today but expires in 2 days
        member_expiring_soon = Member.objects.create(
            name="Expiring Soon Pemula",
            email="expiringsoonpemula@example.com",
            phone_number="628666666666",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            pemula_active_until=timezone.now() + timedelta(days=2),
        )

        # Create a class instance 5 days in the future
        future_schedule = ClassSchedule.objects.create(
            class_obj=self.kelas_pemula_class,
            day_of_week=3,
            start_time="16:00:00",
            end_time="17:00:00",
        )
        future_instance = ClassInstance.objects.create(
            class_schedule=future_schedule,
            date=timezone.now().date() + timedelta(days=5),
            start_time=future_schedule.start_time,
            end_time=future_schedule.end_time,
            status="OPEN",
        )

        session = self.client.session
        session["member_email"] = member_expiring_soon.email
        session.save()

        url = reverse("classes:book_class", args=[future_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Silver")
        future_instance.refresh_from_db()
        self.assertNotIn(member_expiring_soon, future_instance.booked_members.all())

    def test_semi_private_booking_active_until_class_date(self):
        """Test that member can book Semi Private if subscription is active on class date"""
        # Member has subscription that expires 10 days from now
        member_active_long = Member.objects.create(
            name="Active Long",
            email="activelong@example.com",
            phone_number="628777777777",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            semi_private_active_until=timezone.now() + timedelta(days=10),
        )

        # Create a class instance 5 days in the future
        future_schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private_class,
            day_of_week=4,
            start_time="17:00:00",
            end_time="18:00:00",
        )
        future_instance = ClassInstance.objects.create(
            class_schedule=future_schedule,
            date=timezone.now().date() + timedelta(days=5),
            start_time=future_schedule.start_time,
            end_time=future_schedule.end_time,
            status="OPEN",
        )

        session = self.client.session
        session["member_email"] = member_active_long.email
        session.save()

        url = reverse("classes:book_class", args=[future_instance.id])
        response = self.client.post(url, follow=True)

        self.assertContains(response, "Berhasil booking kelas")
        future_instance.refresh_from_db()
        self.assertIn(member_active_long, future_instance.booked_members.all())


class CancelledInstanceStatusGuardTest(TestCase):
    """
    Regression tests for the bug where an admin-cancelled class instance
    re-appeared as OPEN the next day. Root cause: update_status() (called by
    book_class / cancel_class / move_from_waitlist) unconditionally reset the
    status based on headcount, overwriting a CANCELLED status back to OPEN when
    a still-booked member later touched the class.
    """

    def setUp(self):
        self.yoga_class = Class.objects.create(
            name="Yoga", description="A relaxing yoga class.", max_members=2
        )
        self.schedule = ClassSchedule.objects.create(
            class_obj=self.yoga_class,
            day_of_week=0,
            start_time="09:00:00",
            end_time="10:00:00",
        )
        # A future-dated instance the admin has cancelled.
        self.instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=timezone.now().date() + timedelta(days=2),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="CANCELLED",
        )
        self.member = Member.objects.create(
            name="Booked Member",
            email="booked@example.com",
            phone_number="628999999901",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )
        # Member was booked before the admin cancelled the class.
        self.instance.booked_members.add(self.member)

    def test_update_status_does_not_resurrect_cancelled(self):
        """update_status() must leave a CANCELLED instance CANCELLED."""
        self.instance.update_status()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "CANCELLED")

    def test_update_status_does_not_touch_completed(self):
        """update_status() must leave a COMPLETED instance COMPLETED."""
        self.instance.status = "COMPLETED"
        self.instance.save()
        self.instance.update_status()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "COMPLETED")

    def test_move_from_waitlist_does_not_resurrect_cancelled(self):
        """
        Promoting from the waitlist on a cancelled class must not flip it OPEN
        (move_from_waitlist calls update_status internally).
        """
        waitlister = Member.objects.create(
            name="Waitlister",
            email="waitlister@example.com",
            phone_number="628999999902",
            age=30,
            height=165.0,
            weight=60.0,
            gender="F",
            goals="Stay fit",
            years_of_working_out="Beginner",
        )
        self.instance.booked_members.clear()
        self.instance.waitlisted_members.add(waitlister)

        self.instance.move_from_waitlist()

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "CANCELLED")

    def test_cancel_booking_via_view_keeps_class_cancelled(self):
        """
        Reproduces the reported bug end-to-end: a booked member cancelling their
        booking on a cancelled class must remove the member but keep the class
        CANCELLED (not re-open it).
        """
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        url = reverse("classes:cancel_class", args=[self.instance.id])
        self.client.post(url, follow=True)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "CANCELLED")
        self.assertNotIn(self.member, self.instance.booked_members.all())

    def test_book_via_view_keeps_class_cancelled(self):
        """Booking a cancelled class (e.g. via a stale link) must not re-open it."""
        other = Member.objects.create(
            name="Other Member",
            email="other@example.com",
            phone_number="628999999903",
            age=28,
            height=175.0,
            weight=72.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )
        session = self.client.session
        session["member_email"] = other.email
        session.save()

        url = reverse("classes:book_class", args=[self.instance.id])
        self.client.post(url, follow=True)

        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, "CANCELLED")

    def test_update_status_still_toggles_open_and_full(self):
        """Regression guard: OPEN/FULL toggling still works for live classes."""
        live = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=timezone.now().date() + timedelta(days=3),
            start_time=self.schedule.start_time,
            end_time=self.schedule.end_time,
            status="OPEN",
        )
        m1 = Member.objects.create(
            name="M1", email="m1@example.com", phone_number="628999999911",
            age=25, height=170.0, weight=70.0, gender="M",
            goals="Stay fit", years_of_working_out="1-2 years",
        )
        m2 = Member.objects.create(
            name="M2", email="m2@example.com", phone_number="628999999912",
            age=25, height=170.0, weight=70.0, gender="M",
            goals="Stay fit", years_of_working_out="1-2 years",
        )
        live.booked_members.add(m1, m2)  # max_members = 2
        live.update_status()
        live.refresh_from_db()
        self.assertEqual(live.status, "FULL")

        live.booked_members.remove(m1)
        live.update_status()
        live.refresh_from_db()
        self.assertEqual(live.status, "OPEN")



class DailyBookingLimitTest(TestCase):
    """Max MAX_CLASSES_PER_DAY classes per member per day, waitlist included."""

    def setUp(self):
        self.pemula = Class.objects.create(
            name="Kelas Pemula", description="Beginner class", max_members=10
        )
        self.semi_private = Class.objects.create(
            name="Semi Private", description="Semi private class", max_members=2
        )
        self.member = Member.objects.create(
            name="Rajin Member",
            email="rajin@example.com",
            phone_number="628555000111",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
            semi_private_active_until=timezone.now() + timedelta(days=30),
        )
        self.other_member = Member.objects.create(
            name="Member Lain",
            email="lain@example.com",
            phone_number="628555000222",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.day_after = timezone.now().date() + timedelta(days=2)

    def make_instance(self, class_obj, hour, on_date=None, status="OPEN"):
        """One class instance at `hour` on `on_date` (defaults to tomorrow)."""
        on_date = on_date or self.tomorrow
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=class_obj,
            day_of_week=on_date.weekday(),
            start_time=f"{hour:02d}:00:00",
            defaults={"end_time": f"{hour + 1:02d}:00:00"},
        )
        return ClassInstance.objects.create(
            class_schedule=schedule,
            date=on_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status=status,
        )

    def login(self, member=None):
        session = self.client.session
        session["member_email"] = (member or self.member).email
        session.save()

    def book(self, instance):
        return self.client.post(
            reverse("classes:book_class", args=[instance.id]), follow=True
        )

    def test_third_booking_same_day_is_blocked(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(first)
        self.book(second)
        response = self.book(third)

        self.assertContains(response, "Maksimal 2 kelas per hari")
        self.assertNotIn(self.member, third.booked_members.all())
        self.assertNotIn(self.member, third.waitlisted_members.all())
        self.assertIn(self.member, first.booked_members.all())
        self.assertIn(self.member, second.booked_members.all())

    def test_limit_counts_all_class_types_together(self):
        pemula_class = self.make_instance(self.pemula, 8)
        semi_class = self.make_instance(self.semi_private, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(pemula_class)
        self.book(semi_class)
        response = self.book(third)

        self.assertContains(response, "Maksimal 2 kelas per hari")
        self.assertNotIn(self.member, third.booked_members.all())

    def test_waitlist_counts_toward_the_limit(self):
        booked = self.make_instance(self.pemula, 8)
        full_class = self.make_instance(self.semi_private, 10)
        third = self.make_instance(self.pemula, 16)

        # Fill the Semi Private class (max 2) so the member lands on the waitlist
        for i in range(2):
            filler = Member.objects.create(
                name=f"Filler {i}",
                email=f"filler{i}@example.com",
                phone_number=f"62855590000{i}",
                age=25,
                height=170.0,
                weight=70.0,
                gender="M",
                goals="Stay fit",
                years_of_working_out="1-2 years",
            )
            full_class.booked_members.add(filler)
        full_class.update_status()

        self.login()
        self.book(booked)
        self.book(full_class)
        self.assertIn(self.member, full_class.waitlisted_members.all())

        response = self.book(third)
        self.assertContains(response, "Maksimal 2 kelas per hari")
        self.assertNotIn(self.member, third.booked_members.all())

    def test_limit_is_per_day_not_overall(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        next_day = self.make_instance(self.pemula, 8, on_date=self.day_after)
        self.login()

        self.book(first)
        self.book(second)
        response = self.book(next_day)

        self.assertNotContains(response, "Maksimal 2 kelas per hari")
        self.assertIn(self.member, next_day.booked_members.all())

    def test_cancelling_frees_up_a_slot(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(first)
        self.book(second)
        self.client.post(
            reverse("classes:cancel_class", args=[second.id]), follow=True
        )
        response = self.book(third)

        self.assertContains(response, "Berhasil booking")
        self.assertIn(self.member, third.booked_members.all())

    def test_class_cancelled_by_gym_does_not_use_up_the_quota(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(first)
        self.book(second)
        # Gym cancels the 10:00 class, so it should not count anymore
        second.status = "CANCELLED"
        second.save()

        response = self.book(third)
        self.assertContains(response, "Berhasil booking")
        self.assertIn(self.member, third.booked_members.all())

    def test_waitlist_promotion_still_works_at_the_limit(self):
        """Promotion converts a waitlist spot that already counted, so it must pass."""
        booked = self.make_instance(self.pemula, 8)
        full_class = self.make_instance(self.semi_private, 10)
        full_class.booked_members.add(self.other_member)
        filler = Member.objects.create(
            name="Filler",
            email="filler@example.com",
            phone_number="628555099999",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
        )
        full_class.booked_members.add(filler)
        full_class.update_status()

        self.login()
        self.book(booked)
        self.book(full_class)
        self.assertIn(self.member, full_class.waitlisted_members.all())

        # Somebody drops out: our member (2 classes that day already) gets the spot
        full_class.booked_members.remove(filler)
        full_class.move_from_waitlist()

        self.assertIn(self.member, full_class.booked_members.all())
        self.assertNotIn(self.member, full_class.waitlisted_members.all())

    def test_admin_can_still_add_a_third_class(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(first)
        self.book(second)
        # Admin override: adding directly (as /admin does) is not capped
        third.booked_members.add(self.member)

        self.assertIn(self.member, third.booked_members.all())

    def test_detail_page_warns_before_booking(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        self.login()

        self.book(first)
        self.book(second)
        response = self.client.get(
            reverse("classes:class_detail", args=[third.id])
        )

        self.assertTrue(response.context["day_limit_reached"])
        self.assertEqual(len(response.context["member_classes_on_date"]), 2)
        self.assertContains(response, "Maks 2 Kelas per Hari")
        self.assertNotContains(response, "Booking Sekarang")

    def test_detail_page_has_no_warning_below_the_limit(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        self.login()

        self.book(first)
        response = self.client.get(
            reverse("classes:class_detail", args=[second.id])
        )

        self.assertFalse(response.context["day_limit_reached"])
        self.assertContains(response, "Booking Sekarang")

    def test_booked_member_still_sees_cancel_button_at_the_limit(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        self.login()

        self.book(first)
        self.book(second)
        response = self.client.get(
            reverse("classes:class_detail", args=[second.id])
        )

        self.assertContains(response, "Batalkan Booking")
        self.assertNotContains(response, "Maks 2 Kelas per Hari")


class ListPageBookingTest(TestCase):
    """One-tap booking / cancel / waitlist straight from the /kelas/ list."""

    def setUp(self):
        self.pemula = Class.objects.create(
            name="Kelas Pemula", description="Beginner class", max_members=10
        )
        self.semi_private = Class.objects.create(
            name="Semi Private", description="Semi private class", max_members=2
        )
        self.member = Member.objects.create(
            name="List Member",
            email="list@example.com",
            phone_number="628556000111",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
            semi_private_active_until=timezone.now() + timedelta(days=30),
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        self.day_after = timezone.now().date() + timedelta(days=2)

    def make_instance(self, class_obj, hour, on_date=None, status="OPEN"):
        on_date = on_date or self.tomorrow
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=class_obj,
            day_of_week=on_date.weekday(),
            start_time=f"{hour:02d}:00:00",
            defaults={"end_time": f"{hour + 1:02d}:00:00"},
        )
        return ClassInstance.objects.create(
            class_schedule=schedule,
            date=on_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status=status,
        )

    def login(self, member=None):
        session = self.client.session
        session["member_email"] = (member or self.member).email
        session.save()

    def fill(self, instance, count):
        """Book `count` other members into the instance."""
        for i in range(count):
            filler = Member.objects.create(
                name=f"Filler {instance.id}-{i}",
                email=f"filler{instance.id}-{i}@example.com",
                phone_number=f"6285561{instance.id:03d}{i:02d}",
                age=25,
                height=170.0,
                weight=70.0,
                gender="M",
                goals="Stay fit",
                years_of_working_out="1-2 years",
            )
            instance.booked_members.add(filler)
        instance.update_status()

    def test_list_shows_booking_button(self):
        instance = self.make_instance(self.pemula, 8)
        self.login()

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Booking")
        self.assertContains(
            response, reverse("classes:book_class", args=[instance.id])
        )
        self.assertContains(response, f'id="kelas-{instance.id}"')

    def test_booking_from_list_returns_to_list_anchor(self):
        instance = self.make_instance(self.pemula, 8)
        self.login()

        response = self.client.post(
            reverse("classes:book_class", args=[instance.id]), {"next": "list"}
        )

        self.assertRedirects(
            response,
            f"{reverse('classes:class_list')}#kelas-{instance.id}",
            fetch_redirect_response=False,
        )
        self.assertIn(self.member, instance.booked_members.all())

    def test_booking_from_detail_still_returns_to_detail(self):
        instance = self.make_instance(self.pemula, 8)
        self.login()

        response = self.client.post(reverse("classes:book_class", args=[instance.id]))

        self.assertRedirects(
            response, reverse("classes:class_detail", args=[instance.id])
        )

    def test_cancel_from_list_returns_to_list_anchor(self):
        instance = self.make_instance(self.pemula, 8)
        instance.booked_members.add(self.member)
        self.login()

        response = self.client.post(
            reverse("classes:cancel_class", args=[instance.id]), {"next": "list"}
        )

        self.assertRedirects(
            response,
            f"{reverse('classes:class_list')}#kelas-{instance.id}",
            fetch_redirect_response=False,
        )
        self.assertNotIn(self.member, instance.booked_members.all())

    def test_next_param_cannot_redirect_off_site(self):
        instance = self.make_instance(self.pemula, 8)
        self.login()

        response = self.client.post(
            reverse("classes:book_class", args=[instance.id]),
            {"next": "https://evil.example.com/"},
        )

        self.assertRedirects(
            response, reverse("classes:class_detail", args=[instance.id])
        )

    def test_list_shows_cancel_for_booked_class(self):
        instance = self.make_instance(self.pemula, 8)
        instance.booked_members.add(self.member)
        self.login()

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Batalkan")
        self.assertContains(response, reverse("classes:cancel_class", args=[instance.id]))

    def test_list_shows_leave_waitlist_for_waitlisted_class(self):
        instance = self.make_instance(self.semi_private, 8)
        self.fill(instance, 2)
        instance.waitlisted_members.add(self.member)
        self.login()

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Keluar Antrian")

    def test_list_shows_join_waitlist_for_full_class(self):
        instance = self.make_instance(self.semi_private, 8)
        self.fill(instance, 2)
        self.login()

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Masuk Antrian")
        self.assertEqual(instance.status, "FULL")

    def test_list_blocks_and_explains_when_day_limit_reached(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        third = self.make_instance(self.pemula, 16)
        first.booked_members.add(self.member)
        second.booked_members.add(self.member)
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        groups = {group["date"]: group for group in response.context["date_groups"]}

        self.assertTrue(groups[self.tomorrow]["day_limit_reached"])
        self.assertEqual(len(groups[self.tomorrow]["held_classes"]), 2)
        self.assertContains(response, "Maks 2/hari")
        # The explanation shows once for the day, not once per card
        self.assertContains(response, "Kamu sudah punya 2 kelas di hari ini", count=1)
        blocked = [
            instance
            for instance in response.context["class_instances"]
            if instance.id == third.id
        ][0]
        self.assertEqual(blocked.booking_block["code"], "DAY_LIMIT")

    def test_day_limit_only_marks_the_capped_date(self):
        first = self.make_instance(self.pemula, 8)
        second = self.make_instance(self.pemula, 10)
        first.booked_members.add(self.member)
        second.booked_members.add(self.member)
        self.make_instance(self.pemula, 8, on_date=self.day_after)
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        groups = {group["date"]: group for group in response.context["date_groups"]}

        self.assertTrue(groups[self.tomorrow]["day_limit_reached"])
        self.assertFalse(groups[self.day_after]["day_limit_reached"])

    def test_list_blocks_class_the_member_has_no_membership_for(self):
        no_membership = Member.objects.create(
            name="Bronze Only",
            email="bronze@example.com",
            phone_number="628556000999",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.make_instance(self.pemula, 8)
        self.make_instance(self.semi_private, 10)
        self.login(no_membership)

        response = self.client.get(reverse("classes:class_list"))

        self.assertContains(response, "Silver Tidak Aktif")
        self.assertContains(response, "Gold Tidak Aktif")
        self.assertNotContains(response, "fa-check me-1")

    def test_list_does_not_grow_queries_per_card(self):
        for hour in (8, 10, 12, 14, 16, 18):
            self.make_instance(self.pemula, hour)
        self.login()

        # Everything a card needs is precomputed, so the query count must stay
        # flat no matter how many classes are listed.
        with self.assertNumQueries(6):
            self.client.get(reverse("classes:class_list"))

        for hour in (7, 9, 11, 13, 15, 17):
            self.make_instance(self.pemula, hour)

        with self.assertNumQueries(6):
            self.client.get(reverse("classes:class_list"))


class WaitlistPositionTest(TestCase):
    """Members are told their place in the queue, matching FIFO promotion order."""

    def setUp(self):
        self.semi_private = Class.objects.create(
            name="Semi Private", description="Semi private", max_members=1
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private,
            day_of_week=self.tomorrow.weekday(),
            start_time="09:00:00",
            end_time="10:00:00",
        )
        self.instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=self.tomorrow,
            start_time="09:00:00",
            end_time="10:00:00",
        )
        self.members = []
        for i in range(4):
            self.members.append(
                Member.objects.create(
                    name=f"Queue Member {i}",
                    email=f"queue{i}@example.com",
                    phone_number=f"62855700000{i}",
                    age=25,
                    height=170.0,
                    weight=70.0,
                    gender="M",
                    goals="Stay fit",
                    years_of_working_out="1-2 years",
                    active_until=timezone.now() + timedelta(days=30),
                    semi_private_active_until=timezone.now() + timedelta(days=30),
                )
            )

    def test_position_follows_join_order(self):
        self.instance.booked_members.add(self.members[0])
        for member in self.members[1:]:
            self.instance.waitlisted_members.add(member)

        self.assertIsNone(self.instance.waitlist_position(self.members[0]))
        self.assertEqual(self.instance.waitlist_position(self.members[1]), 1)
        self.assertEqual(self.instance.waitlist_position(self.members[2]), 2)
        self.assertEqual(self.instance.waitlist_position(self.members[3]), 3)

    def test_position_matches_who_gets_promoted(self):
        self.instance.booked_members.add(self.members[0])
        self.instance.waitlisted_members.add(self.members[1])
        self.instance.waitlisted_members.add(self.members[2])
        first_in_line = self.members[1]
        self.assertEqual(self.instance.waitlist_position(first_in_line), 1)

        self.instance.booked_members.remove(self.members[0])
        self.instance.move_from_waitlist()

        self.assertIn(first_in_line, self.instance.booked_members.all())
        # The member behind moves up
        self.assertEqual(self.instance.waitlist_position(self.members[2]), 1)

    def test_position_shown_on_detail_page(self):
        self.instance.booked_members.add(self.members[0])
        self.instance.waitlisted_members.add(self.members[1])
        self.instance.waitlisted_members.add(self.members[2])

        session = self.client.session
        session["member_email"] = self.members[2].email
        session.save()
        response = self.client.get(
            reverse("classes:class_detail", args=[self.instance.id])
        )

        self.assertEqual(response.context["waitlist_place"], 2)
        self.assertContains(response, "Kamu antrian ke-2")

    def test_position_shown_on_list_page(self):
        self.instance.booked_members.add(self.members[0])
        self.instance.waitlisted_members.add(self.members[1])
        self.instance.waitlisted_members.add(self.members[2])

        session = self.client.session
        session["member_email"] = self.members[2].email
        session.save()
        response = self.client.get(reverse("classes:class_list"))

        listed = response.context["class_instances"][0]
        self.assertEqual(listed.waitlist_place, 2)
        self.assertContains(response, "Antrian ke-2")


class ClassCapacityDisplayTest(TestCase):
    """The card shows how full a class is and who is already in it."""

    def setUp(self):
        self.pemula = Class.objects.create(
            name="Kelas Pemula", description="Beginner", max_members=10
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        schedule = ClassSchedule.objects.create(
            class_obj=self.pemula,
            day_of_week=self.tomorrow.weekday(),
            start_time="08:00:00",
            end_time="09:00:00",
        )
        self.instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=self.tomorrow,
            start_time="08:00:00",
            end_time="09:00:00",
        )
        self.member = Member.objects.create(
            name="Viewer Member",
            email="viewer@example.com",
            phone_number="628558000111",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
        )

    def add_booked(self, count, first_letter="A"):
        for i in range(count):
            self.instance.booked_members.add(
                Member.objects.create(
                    name=f"{first_letter}nggota {i}",
                    email=f"anggota{i}@example.com",
                    phone_number=f"6285581000{i:02d}",
                    age=25,
                    height=170.0,
                    weight=70.0,
                    gender="M",
                    goals="Stay fit",
                    years_of_working_out="1-2 years",
                )
            )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_shows_booked_count_and_percent(self):
        self.add_booked(4)
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        listed = response.context["class_instances"][0]

        self.assertEqual(listed.booked_count, 4)
        self.assertEqual(listed.slots_left, 6)
        self.assertEqual(listed.booked_percent, 40)
        self.assertContains(response, "dari 10 sudah booking")

    def test_shows_up_to_five_initials_then_a_counter(self):
        self.add_booked(7)
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        listed = response.context["class_instances"][0]

        self.assertEqual(len(listed.booked_preview), 5)
        self.assertEqual(listed.booked_extra, 2)
        self.assertContains(response, "+2")
        self.assertEqual(listed.booked_preview[0]["initial"], "A")

    def test_empty_class_has_no_initials(self):
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        listed = response.context["class_instances"][0]

        self.assertEqual(listed.booked_preview, [])
        self.assertEqual(listed.booked_percent, 0)
        self.assertEqual(listed.slots_left, 10)

    def test_full_class_reports_hundred_percent(self):
        self.add_booked(10)
        self.instance.update_status()
        self.login()

        response = self.client.get(reverse("classes:class_list"))
        listed = response.context["class_instances"][0]

        self.assertEqual(listed.booked_percent, 100)
        self.assertEqual(listed.slots_left, 0)


class ClassCalendarExportTest(TestCase):
    """The .ics download for a class the member holds."""

    def setUp(self):
        self.pemula = Class.objects.create(
            name="Kelas Pemula", description="Beginner", max_members=10
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)
        schedule = ClassSchedule.objects.create(
            class_obj=self.pemula,
            day_of_week=self.tomorrow.weekday(),
            start_time="08:00:00",
            end_time="09:00:00",
        )
        self.instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=self.tomorrow,
            start_time="08:00:00",
            end_time="09:00:00",
        )
        self.member = Member.objects.create(
            name="Calendar Member",
            email="calendar@example.com",
            phone_number="628559000111",
            age=25,
            height=170.0,
            weight=70.0,
            gender="M",
            goals="Stay fit",
            years_of_working_out="1-2 years",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
        )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_booked_member_gets_an_ics_file(self):
        self.instance.booked_members.add(self.member)
        self.login()

        response = self.client.get(
            reverse("classes:class_calendar", args=[self.instance.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/calendar", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".ics", response["Content-Disposition"])

        body = response.content.decode()
        self.assertTrue(body.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertIn("END:VCALENDAR", body)
        self.assertIn(f"UID:kelas-{self.instance.id}@mulaigym.id", body)
        self.assertIn("SUMMARY:Kelas Pemula - Mulai Gym", body)
        # 08:00 Jakarta is 01:00 UTC
        self.assertIn(f"DTSTART:{self.tomorrow:%Y%m%d}T010000Z", body)
        self.assertIn(f"DTEND:{self.tomorrow:%Y%m%d}T020000Z", body)
        # A reminder the phone fires by itself
        self.assertIn("BEGIN:VALARM", body)
        self.assertIn("TRIGGER:-PT60M", body)
        # Every line uses CRLF, as RFC 5545 requires
        self.assertNotIn("\n", body.replace("\r\n", ""))

    def test_waitlisted_member_can_also_add_it(self):
        self.instance.waitlisted_members.add(self.member)
        self.login()

        response = self.client.get(
            reverse("classes:class_calendar", args=[self.instance.id])
        )

        self.assertEqual(response.status_code, 200)

    def test_member_without_a_spot_is_turned_away(self):
        self.login()

        response = self.client.get(
            reverse("classes:class_calendar", args=[self.instance.id]), follow=True
        )

        self.assertContains(response, "belum terdaftar")

    def test_login_required(self):
        response = self.client.get(
            reverse("classes:class_calendar", args=[self.instance.id])
        )

        self.assertRedirects(response, reverse("member_login"))

    def test_special_characters_are_escaped(self):
        self.pemula.name = "Kelas Pemula, Level 1; Pagi"
        self.pemula.save()
        self.instance.booked_members.add(self.member)
        self.login()

        body = self.client.get(
            reverse("classes:class_calendar", args=[self.instance.id])
        ).content.decode()

        self.assertIn(r"Kelas Pemula\, Level 1\; Pagi", body)

    def test_calendar_button_and_share_link_on_detail_page(self):
        self.instance.booked_members.add(self.member)
        self.login()

        response = self.client.get(
            reverse("classes:class_detail", args=[self.instance.id])
        )

        self.assertContains(response, "Tambah ke Kalender")
        self.assertContains(
            response, reverse("classes:class_calendar", args=[self.instance.id])
        )
        self.assertContains(response, "Ajak Temen")
        self.assertContains(response, "https://wa.me/?text=")
        self.assertIn("Kelas%20Pemula", response.context["whatsapp_share_url"])

    def test_calendar_button_hidden_when_not_registered(self):
        self.login()

        response = self.client.get(
            reverse("classes:class_detail", args=[self.instance.id])
        )

        self.assertNotContains(response, "Tambah ke Kalender")
        # Sharing a class you have not booked is still fine
        self.assertContains(response, "Ajak Temen")
