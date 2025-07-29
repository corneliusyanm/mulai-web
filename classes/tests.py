from django.test import TestCase
from django.utils import timezone
from django.core.management import call_command
from datetime import date, timedelta
from io import StringIO
from accounts.models import Member
from classes.models import Class, ClassSchedule, ClassInstance


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
