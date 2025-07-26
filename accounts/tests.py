from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from unittest.mock import Mock

from .models import Member, Tamu, Masukkan, Prospect
from .admin import ProspectAdmin
from .models import User
from visits.admin import admin_site


class MemberModelTest(TestCase):
    def test_is_active_member_with_future_date(self):
        """
        is_active_member should return True if active_until is in the future.
        """
        future_date = timezone.now() + timedelta(days=30)
        member = Member(
            name="Test User",
            email="test@example.com",
            phone_number="6281234567890",
            active_until=future_date,
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
            social_media_username="@testuser",
        )
        self.assertIs(member.is_active_member, True)

    def test_is_active_member_with_past_date(self):
        """
        is_active_member should return False if active_until is in the past.
        """
        past_date = timezone.now() - timedelta(days=30)
        member = Member(
            name="Test User",
            email="test@example.com",
            phone_number="6281234567890",
            active_until=past_date,
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
            social_media_username="@testuser",
        )
        self.assertIs(member.is_active_member, False)

    def test_is_active_member_with_no_date(self):
        """
        is_active_member should return False if active_until is None.
        """
        member = Member(
            name="Test User",
            email="test@example.com",
            phone_number="6281234567890",
            active_until=None,
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
            social_media_username="@testuser",
        )
        self.assertIs(member.is_active_member, False)

    def test_member_creation(self):
        """
        Test that a Member can be created with all the required fields.
        """
        member = Member.objects.create(
            name="John Doe",
            email="john.doe@example.com",
            phone_number="628111222333",
            gender="M",
            age=30,
            height="175.5",
            weight="75.2",
            years_of_working_out="2",
            goals="Get stronger",
            know_mulai_gym_from="Instagram",
            social_media_username="@johndoe",
        )
        self.assertEqual(member.name, "John Doe")
        self.assertEqual(member.email, "john.doe@example.com")
        self.assertEqual(member.phone_number, "628111222333")
        self.assertIs(member.is_active_member, False)

    def test_is_pemula_active_member(self):
        """
        Test the is_pemula_active_member property.
        """
        member = Member.objects.create(
            name="Pemula Member",
            email="pemula@example.com",
            phone_number="6281111111111",
            gender="M",
            age=20,
            height=170,
            weight=70,
            years_of_working_out="0",
            goals="Start",
            know_mulai_gym_from="tiktok",
            social_media_username="@pemula",
        )
        member.pemula_active_until = timezone.now() + timedelta(days=1)
        member.save()
        self.assertTrue(member.is_pemula_active_member)

        member.pemula_active_until = timezone.now() - timedelta(days=1)
        member.save()
        self.assertFalse(member.is_pemula_active_member)


class MemberViewsTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            name="Test User",
            email="test@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
            social_media_username="@testuser",
        )

    def test_member_signup_view(self):
        """
        Test that a member can sign up successfully.
        """
        response = self.client.post(
            reverse("signup"),
            {
                "name": "New User",
                "email": "newuser@example.com",
                "country_code": "+62",
                "phone_number_display": "81234567891",
                "gender": "F",
                "age": 22,
                "height": 160,
                "weight": 55,
                "years_of_working_out": "0",
                "goals": "To get started",
                "know_mulai_gym_from": "internet",
                "social_media_username": "@newuser",
            },
        )
        self.assertEqual(response.status_code, 302)  # Should redirect on success
        self.assertTrue(Member.objects.filter(email="newuser@example.com").exists())
        self.assertEqual(self.client.session.get("member_email"), "newuser@example.com")

    def test_member_login_with_email(self):
        """
        Test that a member can log in with their email.
        """
        response = self.client.post(
            reverse("member_login"), {"email": "test@example.com"}
        )
        self.assertEqual(response.status_code, 302)  # Should redirect on success
        self.assertEqual(self.client.session.get("member_email"), "test@example.com")

    def test_member_login_with_phone(self):
        """
        Test that a member can log in with their phone number.
        """
        response = self.client.post(
            reverse("member_login"),
            {"country_code": "+62", "phone_number_display": "81234567890"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("member_email"), "test@example.com")

    def test_member_login_with_wrong_email(self):
        """
        Test that a member cannot log in with a wrong email.
        """
        response = self.client.post(
            reverse("member_login"), {"email": "wrong@example.com"}
        )
        self.assertEqual(response.status_code, 200)  # Should re-render the form
        self.assertIsNone(self.client.session.get("member_email"))

    def test_member_login_with_wrong_phone(self):
        """
        Test that a member cannot log in with a wrong phone number.
        """
        response = self.client.post(
            reverse("member_login"),
            {"country_code": "+62", "phone_number_display": "11111111111"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get("member_email"))

    def test_signup_with_existing_phone_number(self):
        """
        Test that signup fails if the phone number is already registered.
        """
        response = self.client.post(
            reverse("signup"),
            {
                "name": "Another User",
                "email": "anotheruser@example.com",
                "country_code": "+62",
                "phone_number_display": "81234567890",  # Existing number
                "gender": "F",
                "age": 22,
                "height": 160,
                "weight": 55,
                "years_of_working_out": "0",
                "goals": "To get started",
                "know_mulai_gym_from": "internet",
                "social_media_username": "@anotheruser",
            },
        )
        self.assertEqual(response.status_code, 200)  # Should re-render the form
        self.assertFalse(
            Member.objects.filter(email="anotheruser@example.com").exists()
        )

    def test_member_detail_view(self):
        """
        Test that a logged-in member can view their details.
        """
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()
        response = self.client.get(reverse("member_details"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.member.name)

    def test_member_detail_view_unauthenticated(self):
        """
        Test that a user who is not logged in is redirected from the detail view.
        """
        response = self.client.get(reverse("member_details"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("member_login"))

    def test_member_edit_view(self):
        """
        Test that a logged-in member can edit their information.
        """
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()
        new_name = "Updated Name"
        response = self.client.post(
            reverse("member_edit"),
            {
                "name": new_name,
                "gender": self.member.gender,
                "age": self.member.age,
                "height": self.member.height,
                "weight": self.member.weight,
                "country_code": "+62",
                "phone_number_display": "81234567890",
                "years_of_working_out": self.member.years_of_working_out,
                "goals": self.member.goals,
                "why_choose_mulai": "A new reason",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, new_name)

    def test_member_logout_view(self):
        """
        Test that a member is logged out and the session is cleared.
        """
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        response = self.client.get(reverse("member_logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get("member_email"))


class GuestAndFeedbackTest(TestCase):
    def test_tamu_signup_view(self):
        """
        Test that the guest signup form can be submitted successfully.
        """
        response = self.client.post(
            reverse("tamu_signup"),
            {
                "name": "Test Guest",
                "phone_number": "08123456789",
                "has_worked_out_before": "Never",
                "social_media_username": "testguest",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tamu.objects.filter(name="Test Guest").exists())

    def test_masukkan_view_with_contact(self):
        """
        Test that the feedback form can be submitted successfully with contact info.
        """
        response = self.client.post(
            reverse("masukkan"),
            {
                "name": "Feedback Giver",
                "contact": "08987654321",
                "feedback": "This is great!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Masukkan.objects.filter(name="Feedback Giver").exists())

    def test_masukkan_view_anonymous(self):
        """
        Test that the feedback form can be submitted anonymously.
        """
        response = self.client.post(
            reverse("masukkan"),
            {
                "feedback": "Anonymous feedback.",
            },
        )
        self.assertEqual(response.status_code, 302)
        # Check that a feedback object was created
        self.assertTrue(
            Masukkan.objects.filter(feedback="Anonymous feedback.").exists()
        )


class ProspectTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            "admin_test", "admin@test.com", "password"
        )

    def test_prospect_creation(self):
        """Test that a Prospect can be created successfully."""
        prospect = Prospect.objects.create(
            name="Test Prospect",
            phone_number="628123456789",
            gym_experience="1 year",
            social_media_username="@testprospect",
            notes="Interested in PT.",
            created_by=self.admin_user,
        )
        self.assertEqual(prospect.name, "Test Prospect")
        self.assertEqual(prospect.created_by.username, "admin_test")
        self.assertEqual(str(prospect), "Test Prospect")

    def test_prospect_admin_save_model(self):
        """Test that created_by is set automatically on save in the admin."""
        prospect = Prospect(name="Admin Saved Prospect")

        # Mock the request and admin site
        request = Mock()
        request.user = self.admin_user

        prospect_admin = ProspectAdmin(Prospect, admin_site)
        prospect_admin.save_model(request, prospect, form=None, change=False)

        # Refresh from db to get the saved object
        saved_prospect = Prospect.objects.get(name="Admin Saved Prospect")

        self.assertIsNotNone(saved_prospect.created_by)
        self.assertEqual(saved_prospect.created_by, self.admin_user)

    def test_prospect_admin_readonly_fields_on_change(self):
        """Test that created_by is not changed on update."""
        other_user = User.objects.create_user(
            "other_user", "other@test.com", "password"
        )

        prospect = Prospect.objects.create(
            name="Initial Prospect", created_by=self.admin_user
        )

        # Mock the request and admin site
        request = Mock()
        request.user = other_user  # A different user is making the change

        prospect_admin = ProspectAdmin(Prospect, admin_site)
        prospect_admin.save_model(request, prospect, form=None, change=True)

        # Refresh from db
        updated_prospect = Prospect.objects.get(id=prospect.id)

        # created_by should remain the original user
        self.assertEqual(updated_prospect.created_by, self.admin_user)
