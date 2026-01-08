"""
Unit tests for chatbot API endpoints.
Tests class listing, member lookup, booking, waitlist, and cancellation.
"""

import json
from datetime import time, timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import Member
from classes.models import Class, ClassInstance, ClassSchedule


@override_settings(CHATBOT_API_KEY="test_api_key")
class ChatbotAPITestCase(TestCase):
    """Base test case with common setup."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.api_key_header = {"HTTP_X_API_KEY": "test_api_key"}

        # Create test member
        self.member = Member.objects.create(
            name="Test User",
            phone_number="6281234567890",
            email="test@example.com",
            gender="M",
            age=30,
            height=170,
            weight=70,
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
            semi_private_active_until=timezone.now() + timedelta(days=30),
        )

        # Create class types
        self.semi_private_class = Class.objects.create(
            name="Semi Private",
            description="Semi-private training",
            max_members=4,
        )
        self.pemula_class = Class.objects.create(
            name="Kelas Pemula (Push)",
            description="Beginner push class",
            max_members=6,
        )

        # Create schedules
        tomorrow = timezone.localdate() + timedelta(days=1)
        day_of_week = tomorrow.weekday()

        self.schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private_class,
            day_of_week=day_of_week,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        # Create class instance
        self.class_instance = ClassInstance.objects.create(
            class_schedule=self.schedule,
            date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="OPEN",
        )


class GetClassesAPITest(ChatbotAPITestCase):
    """Tests for GET /api/chatbot/classes/"""

    def test_get_classes_returns_list(self):
        """Should return list of upcoming classes."""
        response = self.client.get("/api/chatbot/classes/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_get_classes_has_required_fields(self):
        """Each class should have required fields."""
        response = self.client.get("/api/chatbot/classes/")
        data = response.json()

        if len(data) > 0:
            required_fields = [
                "id", "class_name", "date", "start_time",
                "end_time", "status", "available_slots", "max_members"
            ]
            for field in required_fields:
                self.assertIn(field, data[0])

    def test_get_classes_excludes_past_classes(self):
        """Should not return classes that have already started."""
        # Create a past class
        yesterday = timezone.localdate() - timedelta(days=1)
        past_schedule = ClassSchedule.objects.create(
            class_obj=self.semi_private_class,
            day_of_week=yesterday.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        ClassInstance.objects.create(
            class_schedule=past_schedule,
            date=yesterday,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="OPEN",
        )

        response = self.client.get("/api/chatbot/classes/")
        data = response.json()

        for c in data:
            self.assertNotEqual(c["date"], yesterday.isoformat())


class GetMemberAPITest(ChatbotAPITestCase):
    """Tests for GET /api/chatbot/member/"""

    def test_get_member_requires_api_key(self):
        """Should require API key."""
        response = self.client.get("/api/chatbot/member/?phone=6281234567890")
        self.assertEqual(response.status_code, 401)

    def test_get_member_by_phone(self):
        """Should return member by phone number."""
        response = self.client.get(
            "/api/chatbot/member/?phone=6281234567890",
            **self.api_key_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test User")
        self.assertEqual(data["phone_number"], "6281234567890")

    def test_get_member_not_found(self):
        """Should return 404 for unknown phone."""
        response = self.client.get(
            "/api/chatbot/member/?phone=9999999999",
            **self.api_key_header
        )
        self.assertEqual(response.status_code, 404)

    def test_get_member_requires_phone_param(self):
        """Should return 400 if phone not provided."""
        response = self.client.get(
            "/api/chatbot/member/",
            **self.api_key_header
        )
        self.assertEqual(response.status_code, 400)


class BookClassAPITest(ChatbotAPITestCase):
    """Tests for POST /api/chatbot/book/"""

    def test_book_class_requires_api_key(self):
        """Should require API key."""
        response = self.client.post(
            "/api/chatbot/book/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_book_class_success(self):
        """Should successfully book a class."""
        response = self.client.post(
            "/api/chatbot/book/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify member is booked
        self.class_instance.refresh_from_db()
        self.assertIn(self.member, self.class_instance.booked_members.all())

    def test_book_class_double_booking_fails(self):
        """Should fail when already booked."""
        self.class_instance.booked_members.add(self.member)

        response = self.client.post(
            "/api/chatbot/book/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("already", data["message"].lower())

    def test_book_full_class_fails(self):
        """Should fail when class is full."""
        # Fill up the class
        for i in range(self.semi_private_class.max_members):
            member = Member.objects.create(
                name=f"Filler {i}",
                phone_number=f"62800000000{i}",
                email=f"filler{i}@example.com",
                gender="M",
                age=25,
                height=170,
                weight=70,
            )
            self.class_instance.booked_members.add(member)

        response = self.client.post(
            "/api/chatbot/book/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("full", data["message"].lower())


class JoinWaitlistAPITest(ChatbotAPITestCase):
    """Tests for POST /api/chatbot/waitlist/"""

    def test_join_waitlist_success(self):
        """Should successfully join waitlist."""
        response = self.client.post(
            "/api/chatbot/waitlist/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify member is waitlisted
        self.class_instance.refresh_from_db()
        self.assertIn(self.member, self.class_instance.waitlisted_members.all())

    def test_join_waitlist_when_booked_fails(self):
        """Should fail when already booked."""
        self.class_instance.booked_members.add(self.member)

        response = self.client.post(
            "/api/chatbot/waitlist/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        data = response.json()
        self.assertFalse(data["success"])


class CancelBookingAPITest(ChatbotAPITestCase):
    """Tests for POST /api/chatbot/cancel/"""

    def test_cancel_booking_success(self):
        """Should successfully cancel booking."""
        self.class_instance.booked_members.add(self.member)

        response = self.client.post(
            "/api/chatbot/cancel/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify member is removed
        self.class_instance.refresh_from_db()
        self.assertNotIn(self.member, self.class_instance.booked_members.all())

    def test_cancel_waitlist_success(self):
        """Should successfully leave waitlist."""
        self.class_instance.waitlisted_members.add(self.member)

        response = self.client.post(
            "/api/chatbot/cancel/",
            data=json.dumps({
                "member_id": self.member.id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("waitlist", data["message"].lower())

    def test_cancel_promotes_waitlisted_member(self):
        """Cancellation should promote first waitlisted member."""
        # Fill class and add to waitlist
        fillers = []
        for i in range(self.semi_private_class.max_members):
            member = Member.objects.create(
                name=f"Filler {i}",
                phone_number=f"62800000000{i}",
                email=f"filler{i}@example.com",
                gender="M",
                age=25,
                height=170,
                weight=70,
            )
            self.class_instance.booked_members.add(member)
            fillers.append(member)

        # Add member to waitlist
        self.class_instance.waitlisted_members.add(self.member)
        self.class_instance.status = "FULL"
        self.class_instance.save()

        # Cancel first booked member
        response = self.client.post(
            "/api/chatbot/cancel/",
            data=json.dumps({
                "member_id": fillers[0].id,
                "class_instance_id": self.class_instance.id,
            }),
            content_type="application/json",
            **self.api_key_header
        )

        self.assertTrue(response.json()["success"])

        # Waitlisted member should now be booked
        self.class_instance.refresh_from_db()
        self.assertIn(self.member, self.class_instance.booked_members.all())
        self.assertNotIn(self.member, self.class_instance.waitlisted_members.all())


class GetMyBookingsAPITest(ChatbotAPITestCase):
    """Tests for GET /api/chatbot/my-bookings/"""

    def test_get_my_bookings_empty(self):
        """Should return empty list for member with no bookings."""
        response = self.client.get(
            f"/api/chatbot/my-bookings/?member_id={self.member.id}",
            **self.api_key_header
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_get_my_bookings_with_booking(self):
        """Should return booked classes."""
        self.class_instance.booked_members.add(self.member)

        response = self.client.get(
            f"/api/chatbot/my-bookings/?member_id={self.member.id}",
            **self.api_key_header
        )

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["booking_status"], "booked")

    def test_get_my_bookings_with_waitlist(self):
        """Should return waitlisted classes."""
        self.class_instance.waitlisted_members.add(self.member)

        response = self.client.get(
            f"/api/chatbot/my-bookings/?member_id={self.member.id}",
            **self.api_key_header
        )

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["booking_status"], "waitlisted")
