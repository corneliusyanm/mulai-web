import json
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from urllib.parse import quote

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.urls import resolve, reverse
from unittest.mock import Mock, patch

from .models import Member, ActiveMember, Tamu, Masukkan, Prospect
from .admin import ProspectAdmin, MemberAdmin, ActiveMemberAdmin, SaleInline
from .models import User
from .dates import MONTHS_ID
from .views import VISIT_MILESTONES, _visit_milestone
from visits.admin import admin_site
from visits.models import Visit
from payments.models import Package, Payment
from purchases.models import Product, Sale, SaleItem


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

    def test_member_detail_view_upcoming_classes_filter(self):
        """
        Test that member detail view only shows upcoming classes (today and future).
        """
        from classes.models import Class, ClassSchedule, ClassInstance

        # Create a class and schedule
        test_class = Class.objects.create(
            name="Test Class", description="Test", max_members=10
        )
        schedule = ClassSchedule.objects.create(
            class_obj=test_class,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Create class instances
        past_instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        today_instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=today,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        future_instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        # Book member to all instances
        past_instance.booked_members.add(self.member)
        today_instance.booked_members.add(self.member)
        future_instance.booked_members.add(self.member)

        # Login and check detail view
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        response = self.client.get(reverse("member_details"))
        self.assertEqual(response.status_code, 200)

        # Check context data
        upcoming_booked = response.context["upcoming_booked_classes"]
        past_booked = response.context["past_booked_classes"]

        # Should have today and tomorrow in upcoming
        self.assertEqual(len(upcoming_booked), 2)
        self.assertIn(today_instance, upcoming_booked)
        self.assertIn(future_instance, upcoming_booked)

        # Should have yesterday in past
        self.assertEqual(past_booked.count(), 1)
        self.assertIn(past_instance, past_booked)

    def test_member_detail_view_waitlisted_classes_filter(self):
        """
        Test that member detail view correctly filters waitlisted classes.
        """
        from classes.models import Class, ClassSchedule, ClassInstance

        test_class = Class.objects.create(
            name="Waitlist Test", description="Test", max_members=10
        )
        schedule = ClassSchedule.objects.create(
            class_obj=test_class,
            day_of_week=0,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Create instances
        past_waitlist_instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=yesterday,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )
        future_waitlist_instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=tomorrow,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )

        # Add member to waitlists
        past_waitlist_instance.waitlisted_members.add(self.member)
        future_waitlist_instance.waitlisted_members.add(self.member)

        # Login and check detail view
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        response = self.client.get(reverse("member_details"))

        # Check context data
        upcoming_waitlisted = response.context["upcoming_waitlisted_classes"]
        past_waitlisted = response.context["past_waitlisted_classes"]

        # Should have only tomorrow in upcoming
        self.assertEqual(len(upcoming_waitlisted), 1)
        self.assertIn(future_waitlist_instance, upcoming_waitlisted)

        # Should have yesterday in past
        self.assertEqual(past_waitlisted.count(), 1)
        self.assertIn(past_waitlist_instance, past_waitlisted)

    def test_member_detail_view_no_classes(self):
        """
        Test that member detail view handles members with no classes correctly.
        """
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        response = self.client.get(reverse("member_details"))
        self.assertEqual(response.status_code, 200)

        # All class querysets should be empty
        self.assertEqual(len(response.context["upcoming_booked_classes"]), 0)
        self.assertEqual(response.context["past_booked_classes"].count(), 0)
        self.assertEqual(len(response.context["upcoming_waitlisted_classes"]), 0)
        self.assertEqual(response.context["past_waitlisted_classes"].count(), 0)


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


class IsPemulaCalculationTest(TestCase):
    """Test automatic calculation of is_pemula field during member signup."""

    def test_is_pemula_set_to_true_when_belum(self):
        """Test that is_pemula is True when years_of_working_out contains 'belum'."""
        test_cases = [
            "belum pernah",
            "Belum pernah nge-gym",
            "BELUM",
            "belum ada",
            "saya belum pernah",
        ]

        for i, years_text in enumerate(test_cases):
            with self.subTest(years_text=years_text):
                response = self.client.post(
                    reverse("signup"),
                    {
                        "name": f"Test User {i}",
                        "email": f"test{i}@example.com",
                        "country_code": "+62",
                        "phone_number_display": f"8123456789{i}",
                        "gender": "M",
                        "age": 25,
                        "height": 170,
                        "weight": 65,
                        "address": "Test Address",
                        "years_of_working_out": years_text,
                        "goals": "To be healthy",
                        "know_mulai_gym_from": "friends",
                        "why_choose_mulai": "test",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                member = Member.objects.get(email=f"test{i}@example.com")
                self.assertTrue(member.is_pemula, f"Failed for: {years_text}")

    def test_is_pemula_set_to_false_when_tahun(self):
        """Test that is_pemula is False when years_of_working_out contains 'tahun'."""
        test_cases = [
            "2 tahun",
            "1 tahun setengah",
            "3 TAHUN",
            "sudah tahun",
        ]

        for i, years_text in enumerate(test_cases):
            with self.subTest(years_text=years_text):
                response = self.client.post(
                    reverse("signup"),
                    {
                        "name": f"Test User {i}",
                        "email": f"testfalse{i}@example.com",
                        "country_code": "+62",
                        "phone_number_display": f"8223456789{i}",
                        "gender": "F",
                        "age": 25,
                        "height": 160,
                        "weight": 55,
                        "address": "Test Address",
                        "years_of_working_out": years_text,
                        "goals": "To be healthy",
                        "know_mulai_gym_from": "friends",
                        "why_choose_mulai": "test",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                member = Member.objects.get(email=f"testfalse{i}@example.com")
                self.assertFalse(member.is_pemula, f"Failed for: {years_text}")

    def test_is_pemula_set_to_null_for_other_values(self):
        """Test that is_pemula is None for other values that don't match patterns."""
        test_cases = [
            "sudah 3 bulan",
            "Sudah pernah nge-gym",
            "SUDAH lama",
            "3 bulan",
            "6 minggu",
            "baru mulai",
            "on and off",
            "kadang-kadang",
        ]

        for i, years_text in enumerate(test_cases):
            with self.subTest(years_text=years_text):
                response = self.client.post(
                    reverse("signup"),
                    {
                        "name": f"Test User {i}",
                        "email": f"testnull{i}@example.com",
                        "country_code": "+62",
                        "phone_number_display": f"8323456789{i}",
                        "gender": "M",
                        "age": 25,
                        "height": 170,
                        "weight": 65,
                        "address": "Test Address",
                        "years_of_working_out": years_text,
                        "goals": "To be healthy",
                        "know_mulai_gym_from": "friends",
                        "why_choose_mulai": "test",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                member = Member.objects.get(email=f"testnull{i}@example.com")
                self.assertIsNone(member.is_pemula, f"Failed for: {years_text}")

    def test_is_pemula_edge_cases(self):
        """Test edge cases for is_pemula calculation."""
        # Test case where both 'belum' and 'sudah' appear - 'belum' should take precedence
        response = self.client.post(
            reverse("signup"),
            {
                "name": "Edge Case User",
                "email": "edgecase@example.com",
                "country_code": "+62",
                "phone_number_display": "8423456789",
                "gender": "F",
                "age": 25,
                "height": 160,
                "weight": 55,
                "address": "Test Address",
                "years_of_working_out": "belum pernah tapi sudah pernah denger",
                "goals": "To be healthy",
                "know_mulai_gym_from": "friends",
                "why_choose_mulai": "test",
            },
        )
        self.assertEqual(response.status_code, 302)
        member = Member.objects.get(email="edgecase@example.com")
        self.assertTrue(member.is_pemula)  # 'belum' should take precedence

    def test_is_pemula_form_save_method_directly(self):
        """Test the form save method directly without going through the view."""
        from accounts.forms import MemberSignUpForm

        # Test with 'belum'
        form_data = {
            "name": "Direct Test User",
            "email": "directtest@example.com",
            "country_code": "+62",
            "phone_number_display": "8523456789",
            "gender": "M",
            "age": 25,
            "height": 170,
            "weight": 65,
            "address": "Test Address",
            "years_of_working_out": "belum pernah",
            "goals": "To be healthy",
            "know_mulai_gym_from": "friends",
            "why_choose_mulai": "test",
        }

        form = MemberSignUpForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        member = form.save()
        self.assertTrue(member.is_pemula)


class TamuIsPemulaCalculationTest(TestCase):
    """Test automatic calculation of is_pemula field for Tamu during signup."""

    def test_tamu_is_pemula_set_to_true_when_belum_variations(self):
        """Test that is_pemula is True when has_worked_out_before contains 'belum' variations."""
        test_cases = [
            "belum pernah",
            "Belum pernah nge-gym",
            "BELUM",
            "belom tau",
            "blm pernah",
            "blum ada",
            "belm pernah coba",
            "blon pernah",
            "belon mulai",
        ]

        for i, has_worked_out_text in enumerate(test_cases):
            with self.subTest(has_worked_out_text=has_worked_out_text):
                response = self.client.post(
                    reverse("tamu_signup"),
                    {
                        "name": f"Test Tamu {i}",
                        "phone_number": f"0812345678{i:02d}",
                        "has_worked_out_before": has_worked_out_text,
                        "social_media_username": f"@testtamu{i}",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                tamu = Tamu.objects.get(name=f"Test Tamu {i}")
                self.assertTrue(tamu.is_pemula, f"Failed for: {has_worked_out_text}")

    def test_tamu_is_pemula_set_to_false_when_tahun_variations(self):
        """Test that is_pemula is False when has_worked_out_before contains 'tahun' variations."""
        test_cases = [
            "2 tahun",
            "1 tahun setengah",
            "3 TAHUN",
            "sudah tahun",
            "1 thn",
            "5 year",
        ]

        for i, has_worked_out_text in enumerate(test_cases):
            with self.subTest(has_worked_out_text=has_worked_out_text):
                response = self.client.post(
                    reverse("tamu_signup"),
                    {
                        "name": f"Test Tamu False {i}",
                        "phone_number": f"0822345678{i:02d}",
                        "has_worked_out_before": has_worked_out_text,
                        "social_media_username": f"@testtamufalse{i}",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                tamu = Tamu.objects.get(name=f"Test Tamu False {i}")
                self.assertFalse(tamu.is_pemula, f"Failed for: {has_worked_out_text}")

    def test_tamu_is_pemula_set_to_null_for_other_values(self):
        """Test that is_pemula is None for other values that don't match patterns."""
        test_cases = [
            "sudah 3 bulan",
            "Sudah pernah nge-gym",
            "SUDAH lama",
            "3 bulan",
            "6 minggu",
            "baru mulai",
            "on and off",
            "kadang-kadang",
            "jarang",
        ]

        for i, has_worked_out_text in enumerate(test_cases):
            with self.subTest(has_worked_out_text=has_worked_out_text):
                response = self.client.post(
                    reverse("tamu_signup"),
                    {
                        "name": f"Test Tamu Null {i}",
                        "phone_number": f"0832345678{i:02d}",
                        "has_worked_out_before": has_worked_out_text,
                        "social_media_username": f"@testtamunull{i}",
                    },
                )
                self.assertEqual(
                    response.status_code, 302
                )  # Should redirect on success
                tamu = Tamu.objects.get(name=f"Test Tamu Null {i}")
                self.assertIsNone(tamu.is_pemula, f"Failed for: {has_worked_out_text}")

    def test_tamu_is_pemula_edge_cases(self):
        """Test edge cases for Tamu is_pemula calculation."""
        # Test case where both 'belum' and 'tahun' appear - 'belum' should take precedence
        response = self.client.post(
            reverse("tamu_signup"),
            {
                "name": "Edge Case Tamu",
                "phone_number": "0842345678",
                "has_worked_out_before": "belum pernah tapi sudah tahun",
                "social_media_username": "@edgecasetamu",
            },
        )
        self.assertEqual(response.status_code, 302)
        tamu = Tamu.objects.get(name="Edge Case Tamu")
        self.assertTrue(tamu.is_pemula)  # 'belum' should take precedence

    def test_tamu_form_save_method_directly(self):
        """Test the TamuForm save method directly without going through the view."""
        from accounts.forms import TamuForm

        # Test with 'belum'
        form_data = {
            "name": "Direct Test Tamu",
            "phone_number": "0852345678",
            "has_worked_out_before": "belum pernah",
            "social_media_username": "@directtesttamu",
        }

        form = TamuForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        tamu = form.save()
        self.assertTrue(tamu.is_pemula)

        # Test with 'tahun'
        form_data_2 = {
            "name": "Direct Test Tamu 2",
            "phone_number": "0862345678",
            "has_worked_out_before": "2 tahun",
            "social_media_username": "@directtesttamu2",
        }

        form_2 = TamuForm(data=form_data_2)
        self.assertTrue(form_2.is_valid(), f"Form errors: {form_2.errors}")
        tamu_2 = form_2.save()
        self.assertFalse(tamu_2.is_pemula)

        # Test with other value
        form_data_3 = {
            "name": "Direct Test Tamu 3",
            "phone_number": "0872345678",
            "has_worked_out_before": "kadang-kadang",
            "social_media_username": "@directtesttamu3",
        }

        form_3 = TamuForm(data=form_data_3)
        self.assertTrue(form_3.is_valid(), f"Form errors: {form_3.errors}")
        tamu_3 = form_3.save()
        self.assertIsNone(tamu_3.is_pemula)


class MemberAdminTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.member = Member.objects.create(
            name="Test Member",
            email="member@example.com",
            phone_number="1234567890",
            gender="M",
            age=30,
            height=180,
            weight=80,
            years_of_working_out="2 tahun",
            goals="Get fit",
            know_mulai_gym_from="internet",
        )
        self.product1 = Product.objects.create(name="Protein Shake", price=50000)
        self.product2 = Product.objects.create(name="Energy Bar", price=25000)

    def test_member_admin_inlines_registration(self):
        """
        Test that PaymentInline and SaleInline are registered with MemberAdmin.
        """
        self.assertIn(
            "PaymentInline", [inline.__name__ for inline in MemberAdmin.inlines]
        )
        self.assertIn("SaleInline", [inline.__name__ for inline in MemberAdmin.inlines])

    def test_sale_inline_items_list_display(self):
        """
        Test the items_list method in SaleInline for correct HTML output.
        """
        sale = Sale.objects.create(
            member=self.member,
            payment_method="CASH",
            created_by=self.admin_user,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product1,
            quantity=2,
            price_at_purchase=self.product1.price,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product2,
            quantity=3,
            price_at_purchase=self.product2.price,
        )

        sale_inline = SaleInline(Sale, admin_site)
        items_html = sale_inline.items_list(sale)

        self.assertIn("2x Protein Shake @ Rp 50,000 = Rp 100,000", items_html)
        self.assertIn("3x Energy Bar @ Rp 25,000 = Rp 75,000", items_html)
        self.assertIn("<br/>", items_html)

    def test_sale_inline_empty_items_list(self):
        """
        Test the items_list method when a sale has no items.
        """
        sale = Sale.objects.create(
            member=self.member,
            payment_method="CASH",
            created_by=self.admin_user,
        )
        sale_inline = SaleInline(Sale, admin_site)
        items_html = sale_inline.items_list(sale)
        self.assertEqual(items_html, "No items")

    def test_member_admin_total_payments(self):
        """
        Test the total_payments method in MemberAdmin.
        """
        from payments.models import Package

        # Create some payments for the member
        package = Package.objects.create(
            code="TEST-1", default_price=100000, description="Test Package"
        )
        Payment.objects.create(
            member=self.member,
            package=package,
            amount=100000,
            created_by=self.admin_user,
        )
        Payment.objects.create(
            member=self.member,
            package=package,
            amount=150000,
            created_by=self.admin_user,
        )

        member_admin = MemberAdmin(Member, admin_site)
        total_display = member_admin.total_payments(self.member)
        self.assertEqual(total_display, "Rp 250,000")

    def test_member_admin_total_sales(self):
        """
        Test the total_sales method in MemberAdmin.
        """
        # Create some sales for the member
        sale1 = Sale.objects.create(
            member=self.member,
            payment_method="CASH",
            created_by=self.admin_user,
        )
        SaleItem.objects.create(
            sale=sale1,
            product=self.product1,
            quantity=2,
            price_at_purchase=50000,
        )
        sale1.update_total_amount()

        sale2 = Sale.objects.create(
            member=self.member,
            payment_method="QRIS",
            created_by=self.admin_user,
        )
        SaleItem.objects.create(
            sale=sale2,
            product=self.product2,
            quantity=3,
            price_at_purchase=25000,
        )
        sale2.update_total_amount()

        member_admin = MemberAdmin(Member, admin_site)
        total_display = member_admin.total_sales(self.member)
        self.assertEqual(total_display, "Rp 175,000")

    def test_member_admin_zero_totals(self):
        """
        Test that totals show zero when member has no payments or sales.
        """
        member_admin = MemberAdmin(Member, admin_site)

        total_payments = member_admin.total_payments(self.member)
        self.assertEqual(total_payments, "Rp 0")

        total_sales = member_admin.total_sales(self.member)
        self.assertEqual(total_sales, "Rp 0")


class MemberTrackingFlagsTest(TestCase):
    """Test the admin tracking flags on Member model."""

    def test_default_flag_values(self):
        """Test that tracking flags default to False."""
        member = Member.objects.create(
            name="Flag Test User",
            email="flagtest@example.com",
            phone_number="628999888777",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Test",
            know_mulai_gym_from="test",
        )
        self.assertFalse(member.asked_referral)
        self.assertFalse(member.asked_google_review)
        self.assertFalse(member.missed_installment)

    def test_flag_can_be_set_true(self):
        """Test that tracking flags can be set to True."""
        member = Member.objects.create(
            name="Flag True User",
            email="flagtrue@example.com",
            phone_number="628999888666",
            gender="F",
            age=28,
            height=165,
            weight=55,
            years_of_working_out="belum",
            goals="Test",
            know_mulai_gym_from="test",
            asked_referral=True,
            asked_google_review=True,
            missed_installment=True,
        )
        self.assertTrue(member.asked_referral)
        self.assertTrue(member.asked_google_review)
        self.assertTrue(member.missed_installment)

    def test_flag_update(self):
        """Test that tracking flags can be updated."""
        member = Member.objects.create(
            name="Flag Update User",
            email="flagupdate@example.com",
            phone_number="628999888555",
            gender="M",
            age=30,
            height=175,
            weight=80,
            years_of_working_out="2 tahun",
            goals="Test",
            know_mulai_gym_from="test",
        )
        self.assertFalse(member.asked_referral)

        member.asked_referral = True
        member.save()
        member.refresh_from_db()
        self.assertTrue(member.asked_referral)


class ActiveMemberProxyModelTest(TestCase):
    """Test the ActiveMember proxy model."""

    def setUp(self):
        self.active_member = Member.objects.create(
            name="Active User",
            email="active@example.com",
            phone_number="628111222333",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Test",
            know_mulai_gym_from="test",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.expired_member = Member.objects.create(
            name="Expired User",
            email="expired@example.com",
            phone_number="628111222444",
            gender="F",
            age=28,
            height=165,
            weight=55,
            years_of_working_out="belum",
            goals="Test",
            know_mulai_gym_from="test",
            active_until=timezone.now() - timedelta(days=30),
        )

    def test_active_member_is_proxy(self):
        """Test that ActiveMember is a proxy model of Member."""
        self.assertTrue(ActiveMember._meta.proxy)
        self.assertEqual(ActiveMember._meta.proxy_for_model, Member)

    def test_active_member_queryset_same_as_member(self):
        """Test that ActiveMember queries the same table as Member."""
        # Both should exist in ActiveMember.objects.all() since no filter applied yet
        all_members = Member.objects.all()
        self.assertEqual(all_members.count(), 2)


class ActiveMemberAdminTest(TestCase):
    """Test the ActiveMemberAdmin functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            "admin_active", "admin_active@example.com", "password"
        )
        self.active_member = Member.objects.create(
            name="Active Admin Test",
            email="activeadmin@example.com",
            phone_number="628555666777",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Test",
            know_mulai_gym_from="test",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.expired_member = Member.objects.create(
            name="Expired Admin Test",
            email="expiredadmin@example.com",
            phone_number="628555666888",
            gender="F",
            age=28,
            height=165,
            weight=55,
            years_of_working_out="belum",
            goals="Test",
            know_mulai_gym_from="test",
            active_until=timezone.now() - timedelta(days=30),
        )

    def test_active_member_admin_queryset_filters_active_only(self):
        """Test that ActiveMemberAdmin only shows active members."""
        request = self.factory.get("/admin/accounts/activemember/")
        request.user = self.admin_user

        admin_instance = ActiveMemberAdmin(ActiveMember, admin_site)
        queryset = admin_instance.get_queryset(request)

        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.active_member, queryset)
        self.assertNotIn(self.expired_member, queryset)

    def test_active_member_admin_inherits_from_member_admin(self):
        """Test that ActiveMemberAdmin inherits from MemberAdmin."""
        self.assertTrue(issubclass(ActiveMemberAdmin, MemberAdmin))

    def test_active_member_admin_list_editable_includes_flags(self):
        """Test that the tracking flags are list_editable in ActiveMemberAdmin."""
        self.assertIn("asked_referral", ActiveMemberAdmin.list_editable)
        self.assertIn("asked_google_review", ActiveMemberAdmin.list_editable)
        self.assertIn("missed_installment", ActiveMemberAdmin.list_editable)

    def test_active_member_csv_export(self):
        """Test the CSV export for active members."""
        request = self.factory.get("/admin/accounts/activemember/export-csv/")
        request.user = self.admin_user

        admin_instance = ActiveMemberAdmin(ActiveMember, admin_site)
        response = admin_instance.export_active_members_csv(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("active_members_", response["Content-Disposition"])

        # Check content includes active member but not expired
        content = response.content.decode("utf-8")
        self.assertIn("Active Admin Test", content)
        self.assertNotIn("Expired Admin Test", content)


class MemberAdminCSVExportTest(TestCase):
    """Test the CSV export functionality in MemberAdmin."""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            "admin_csv", "admin_csv@example.com", "password"
        )
        self.member = Member.objects.create(
            name="CSV Test User",
            email="csvtest@example.com",
            phone_number="628777888999",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Test goals",
            know_mulai_gym_from="Instagram",
            asked_referral=True,
            asked_google_review=False,
            missed_installment=True,
        )

    def test_member_csv_export_all(self):
        """Test the CSV export for all members."""
        request = self.factory.get("/admin/accounts/member/export-csv/")
        request.user = self.admin_user

        admin_instance = MemberAdmin(Member, admin_site)
        response = admin_instance.export_members_csv(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("members_", response["Content-Disposition"])

        # Check content
        content = response.content.decode("utf-8")
        self.assertIn("CSV Test User", content)
        self.assertIn("csvtest@example.com", content)
        # Check flags are included
        self.assertIn("asked_referral", content)  # Header
        self.assertIn("True", content)  # asked_referral value


class MemberHistoryViewTest(TestCase):
    """Tests for /akun/riwayat/ (full, unlimited history)."""

    def setUp(self):
        self.member = Member.objects.create(
            name="History User",
            email="history@example.com",
            phone_number="6281234500001",
            gender="M",
            age=30,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def create_visits(self, count, start_days_ago=0):
        """Create visits on distinct days (check_in_time is auto_now_add, so update it)."""
        for i in range(count):
            visit = Visit.objects.create(member=self.member)
            check_in = timezone.now() - timedelta(days=start_days_ago + i)
            Visit.objects.filter(pk=visit.pk).update(
                check_in_time=check_in,
                check_out_time=check_in + timedelta(hours=1, minutes=15),
            )

    def create_past_class(self, days_ago, waitlist=False):
        from classes.models import Class, ClassSchedule, ClassInstance

        class_obj, _ = Class.objects.get_or_create(
            name="Kelas Pemula", defaults={"max_members": 10}
        )
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=class_obj,
            day_of_week=0,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=timezone.now().date() - timedelta(days=days_ago),
            start_time=time(8, 0),
            end_time=time(9, 0),
            status="COMPLETED",
        )
        if waitlist:
            instance.waitlisted_members.add(self.member)
        else:
            instance.booked_members.add(self.member)
        return instance

    def test_requires_login(self):
        response = self.client.get(reverse("member_history"))
        self.assertRedirects(response, reverse("member_login"))

    def test_shows_all_visits_not_limited(self):
        self.create_visits(12)
        self.login()
        response = self.client.get(reverse("member_history"))
        self.assertEqual(response.status_code, 200)
        rows = [row for group in response.context["groups"] for row in group["rows"]]
        self.assertEqual(len(rows), 12)
        self.assertEqual(response.context["active_tab"], "kunjungan")
        self.assertEqual(response.context["total_rows"], 12)

    def test_visits_are_grouped_by_month_newest_first(self):
        self.create_visits(2)  # this month
        self.create_visits(2, start_days_ago=70)  # ~2 months ago
        self.login()
        response = self.client.get(reverse("member_history"))
        groups = response.context["groups"]
        self.assertGreaterEqual(len(groups), 2)
        keys = [group["key"] for group in groups]
        self.assertEqual(keys, sorted(keys, reverse=True))

    def test_visit_duration_label(self):
        self.create_visits(1)
        self.login()
        response = self.client.get(reverse("member_history"))
        visit = response.context["groups"][0]["rows"][0]
        self.assertEqual(visit.duration_label, "1j 15m")

    def test_payments_tab_shows_all_payments(self):
        for i in range(8):
            Payment.objects.create(
                member=self.member,
                amount=150000,
                payment_date=timezone.now() - timedelta(days=30 * i),
            )
        self.login()
        response = self.client.get(reverse("member_history"), {"tab": "pembayaran"})
        self.assertEqual(response.status_code, 200)
        rows = [row for group in response.context["groups"] for row in group["rows"]]
        self.assertEqual(len(rows), 8)
        self.assertEqual(response.context["active_tab"], "pembayaran")

    def test_classes_tab_shows_booked_and_waitlisted(self):
        self.create_past_class(days_ago=3)
        self.create_past_class(days_ago=10)
        self.create_past_class(days_ago=20, waitlist=True)
        self.login()
        response = self.client.get(reverse("member_history"), {"tab": "kelas"})
        self.assertEqual(response.status_code, 200)
        rows = [row for group in response.context["groups"] for row in group["rows"]]
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(1 for row in rows if row["is_waitlist"]), 1)

    def test_classes_tab_excludes_upcoming(self):
        from classes.models import Class, ClassSchedule, ClassInstance

        self.create_past_class(days_ago=3)
        class_obj = Class.objects.get(name="Kelas Pemula")
        schedule = ClassSchedule.objects.filter(class_obj=class_obj).first()
        upcoming = ClassInstance.objects.create(
            class_schedule=schedule,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        upcoming.booked_members.add(self.member)
        self.login()
        response = self.client.get(reverse("member_history"), {"tab": "kelas"})
        rows = [row for group in response.context["groups"] for row in group["rows"]]
        self.assertEqual(len(rows), 1)

    def test_unknown_tab_falls_back_to_kunjungan(self):
        self.login()
        response = self.client.get(reverse("member_history"), {"tab": "ngawur"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_tab"], "kunjungan")

    def test_empty_history_renders(self):
        self.login()
        response = self.client.get(reverse("member_history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["groups"], [])
        self.assertContains(response, "Belum ada riwayat")

    def test_detail_view_hides_button_when_nothing_more(self):
        self.create_visits(3)
        self.login()
        response = self.client.get(reverse("member_details"))
        self.assertFalse(response.context["has_more_visits"])
        self.assertNotContains(response, "Lihat Semua Kunjungan")

    def test_detail_view_shows_button_when_more_history(self):
        self.create_visits(7)
        self.login()
        response = self.client.get(reverse("member_details"))
        self.assertTrue(response.context["has_more_visits"])
        self.assertEqual(response.context["total_visits"], 7)
        self.assertContains(response, "Lihat Semua Kunjungan")
        self.assertContains(response, reverse("member_history"))
        # The trimmed list itself stays at 5 rows
        self.assertEqual(len(response.context["recent_visits"]), 5)

    def test_detail_view_shows_class_history_button(self):
        for i in range(11):
            self.create_past_class(days_ago=i + 1)
        self.login()
        response = self.client.get(reverse("member_details"))
        self.assertTrue(response.context["has_more_past_classes"])
        self.assertEqual(response.context["total_past_classes"], 11)
        self.assertContains(response, "Lihat Semua Riwayat Kelas")


class UpcomingClassCountdownTest(TestCase):
    """The account page says when a class starts, in words."""

    def setUp(self):
        from classes.models import Class, ClassSchedule, ClassInstance

        self.Class = Class
        self.ClassSchedule = ClassSchedule
        self.ClassInstance = ClassInstance
        self.member = Member.objects.create(
            name="Countdown Member",
            email="countdown@example.com",
            phone_number="628560000111",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.class_obj = Class.objects.create(
            name="Kelas Pemula", description="Beginner", max_members=10
        )

    def book_at(self, start_dt, hours=1):
        local_start = timezone.localtime(start_dt)
        schedule, _ = self.ClassSchedule.objects.get_or_create(
            class_obj=self.class_obj,
            day_of_week=local_start.weekday(),
            start_time=local_start.time().replace(second=0, microsecond=0),
            defaults={
                "end_time": (local_start + timedelta(hours=hours))
                .time()
                .replace(second=0, microsecond=0)
            },
        )
        instance = self.ClassInstance.objects.create(
            class_schedule=schedule,
            date=local_start.date(),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        )
        instance.booked_members.add(self.member)
        return instance

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def upcoming(self, response):
        return response.context["upcoming_booked_classes"]

    def test_minutes_when_it_starts_very_soon(self):
        self.book_at(timezone.now() + timedelta(minutes=40))
        self.login()

        booking = self.upcoming(self.client.get(reverse("member_details")))[0]

        self.assertIn("menit lagi", booking.when_label)
        self.assertTrue(booking.when_soon)

    def test_hours_when_it_starts_later_today(self):
        start = timezone.now() + timedelta(hours=4)
        if timezone.localtime(start).date() != timezone.localdate():
            self.skipTest("4 hours from now is tomorrow, timing-specific case")
        self.book_at(start)
        self.login()

        booking = self.upcoming(self.client.get(reverse("member_details")))[0]

        self.assertIn("jam lagi", booking.when_label)
        self.assertTrue(booking.when_soon)

    def test_tomorrow_shows_the_clock_time(self):
        start = timezone.localtime(timezone.now()) + timedelta(days=1)
        self.book_at(start)
        self.login()

        booking = self.upcoming(self.client.get(reverse("member_details")))[0]

        self.assertTrue(booking.when_label.startswith("Besok"))
        self.assertFalse(booking.when_soon)

    def test_further_away_counts_days(self):
        self.book_at(timezone.localtime(timezone.now()) + timedelta(days=3))
        self.login()

        booking = self.upcoming(self.client.get(reverse("member_details")))[0]

        self.assertEqual(booking.when_label, "3 hari lagi")
        self.assertFalse(booking.when_soon)

    def test_running_right_now(self):
        self.book_at(timezone.now() - timedelta(minutes=20))
        self.login()

        booking = self.upcoming(self.client.get(reverse("member_details")))[0]

        self.assertEqual(booking.when_label, "Sedang berlangsung")
        self.assertTrue(booking.when_soon)

    def test_cancel_nudge_shows_only_with_upcoming_classes(self):
        self.login()
        without = self.client.get(reverse("member_details"))
        self.assertNotContains(without, "biar member lain kebagian")

        self.book_at(timezone.now() + timedelta(days=1))
        with_class = self.client.get(reverse("member_details"))
        self.assertContains(with_class, "biar member lain kebagian")


class VisitHabitStatsTest(TestCase):
    """Monthly count and week streak on the account page."""

    def setUp(self):
        self.member = Member.objects.create(
            name="Habit Member",
            email="habit@example.com",
            phone_number="628561000111",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )

    def visit_days_ago(self, days):
        visit = Visit.objects.create(member=self.member)
        Visit.objects.filter(pk=visit.pk).update(
            check_in_time=timezone.now() - timedelta(days=days)
        )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def stats(self):
        response = self.client.get(reverse("member_details"))
        return response, (
            response.context["visits_this_month"],
            response.context["visit_streak_weeks"],
        )

    def test_no_visits_no_tiles(self):
        self.login()
        response, (this_month, streak) = self.stats()

        self.assertEqual(this_month, 0)
        self.assertEqual(streak, 0)
        self.assertNotContains(response, "Minggu Berturut")

    def test_counts_visits_this_month(self):
        today = timezone.localdate()
        self.visit_days_ago(0)
        self.visit_days_ago(1)
        self.visit_days_ago(2)
        self.login()

        response, (this_month, _) = self.stats()

        expected = sum(
            1
            for days in (0, 1, 2)
            if (today - timedelta(days=days)).month == today.month
        )
        self.assertEqual(this_month, expected)
        self.assertContains(response, "Minggu Berturut")

    def test_streak_counts_consecutive_weeks(self):
        for weeks in range(4):
            self.visit_days_ago(weeks * 7)
        self.login()

        _, (_, streak) = self.stats()

        self.assertEqual(streak, 4)

    def test_streak_survives_a_quiet_current_week(self):
        # Last visit was last week, this week has none yet
        self.visit_days_ago(8)
        self.visit_days_ago(15)
        self.login()

        _, (_, streak) = self.stats()

        self.assertEqual(streak, 2)

    def test_streak_breaks_after_a_missed_week(self):
        self.visit_days_ago(0)
        self.visit_days_ago(21)  # three weeks ago, gap in between
        self.login()

        _, (_, streak) = self.stats()

        self.assertEqual(streak, 1)

    def test_old_visits_alone_give_no_streak(self):
        self.visit_days_ago(60)
        self.login()

        _, (_, streak) = self.stats()

        self.assertEqual(streak, 0)


class HistoryStatDateTest(TestCase):
    """The date tile on each history tab is read by a member, so it is Indonesian.

    All three used strftime("%d %b %Y"), which is right in eight months of the
    year and wrong in Mei, Agu, Okt and Des. Each date here is fixed and picked
    from one of those four.
    """

    def setUp(self):
        self.member = Member.objects.create(
            name="Stat Member",
            email="stat@example.com",
            phone_number="628562000222",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def tile(self, tab, label):
        response = self.client.get(reverse("member_history"), {"tab": tab})
        return next(
            stat["value"]
            for stat in response.context["stats"]
            if stat["label"] == label
        )

    def test_first_visit_tile(self):
        visit = Visit.objects.create(member=self.member)
        Visit.objects.filter(pk=visit.pk).update(
            check_in_time=timezone.make_aware(datetime(2020, 12, 3, 9, 0))
        )

        self.assertEqual(self.tile("kunjungan", "Pertama Kali"), "3 Des 2020")

    def test_last_payment_tile(self):
        Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.make_aware(datetime(2020, 8, 12, 9, 0)),
        )

        self.assertEqual(self.tile("pembayaran", "Terakhir"), "12 Agu 2020")

    def test_last_class_tile(self):
        from classes.models import Class, ClassSchedule, ClassInstance

        class_obj = Class.objects.create(name="Kelas Pemula", max_members=10)
        schedule = ClassSchedule.objects.create(
            class_obj=class_obj,
            day_of_week=0,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=date(2020, 10, 5),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance.booked_members.add(self.member)

        self.assertEqual(self.tile("kelas", "Terakhir"), "5 Okt 2020")


class VisitCalendarTest(TestCase):
    """The month calendar above each month's rows on the full history page.

    Every date here is anchored to last month, which is always fully in the past
    and always has a 10th and a 15th, so nothing in this class depends on which
    day of the month the suite happens to run.
    """

    def setUp(self):
        self.member = Member.objects.create(
            name="Calendar Member",
            email="calendar@example.com",
            phone_number="628562000111",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        self.today = timezone.localdate()
        last_month_end = self.today.replace(day=1) - timedelta(days=1)
        self.month_label = f"{MONTHS_ID[last_month_end.month]} {last_month_end.year}"
        self.tenth = last_month_end.replace(day=10)
        self.fifteenth = last_month_end.replace(day=15)

    def visit_on(self, day, hour=9):
        visit = Visit.objects.create(member=self.member)
        check_in = timezone.make_aware(datetime.combine(day, time(hour, 0)))
        Visit.objects.filter(pk=visit.pk).update(
            check_in_time=check_in, check_out_time=check_in + timedelta(hours=1)
        )

    def class_on(self, day):
        from classes.models import Class, ClassSchedule, ClassInstance

        class_obj, _ = Class.objects.get_or_create(
            name="Kelas Pemula", defaults={"max_members": 10}
        )
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=class_obj,
            day_of_week=day.weekday(),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=day,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance.booked_members.add(self.member)
        return instance

    def cells(self, month):
        return [cell for week in month["weeks"] for cell in week if cell]

    def cell_for(self, month, day_number):
        return next(c for c in self.cells(month) if c["day"] == day_number)

    def last_month(self):
        response = self.client.get(reverse("member_history"))
        month = next(
            m
            for m in response.context["calendar_months"]
            if m["label"] == self.month_label
        )
        return response, month

    def test_one_grid_per_month_that_has_a_visit(self):
        self.visit_on(self.tenth)
        self.visit_on(self.today)
        response = self.client.get(reverse("member_history"))

        months = response.context["calendar_months"]
        self.assertEqual(len(months), 2)
        self.assertEqual(
            [month["label"] for month in months],
            [group["label"] for group in response.context["groups"]],
        )
        for month in months:
            self.assertTrue(month["weeks"])
            for week in month["weeks"]:
                self.assertEqual(len(week), 7)

    def test_every_calendar_comes_before_the_first_visit_row(self):
        self.visit_on(self.tenth)
        self.visit_on(self.today)
        response = self.client.get(reverse("member_history"))
        body = response.content.decode()

        last_grid = body.rindex('class="history-cal-week"')
        first_row = body.index('class="list-group-item')
        self.assertLess(last_grid, first_row)

    def test_grid_holds_every_day_of_the_month_and_nothing_else(self):
        self.visit_on(self.tenth)
        _, month = self.last_month()

        days = sorted(cell["day"] for cell in self.cells(month))
        last_day = (self.today.replace(day=1) - timedelta(days=1)).day
        self.assertEqual(days, list(range(1, last_day + 1)))

    def test_week_starts_on_monday(self):
        self.visit_on(self.tenth)
        response, month = self.last_month()

        self.assertEqual(
            response.context["weekday_labels"],
            ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
        )
        first = self.tenth.replace(day=1)
        self.assertEqual(month["weeks"][0][first.weekday()]["day"], 1)

    def test_a_day_with_a_visit_is_marked(self):
        self.visit_on(self.tenth)
        _, month = self.last_month()

        self.assertTrue(self.cell_for(month, 10)["has_visit"])
        self.assertFalse(self.cell_for(month, 11)["has_visit"])

    def test_two_visits_on_one_day_mark_it_once(self):
        self.visit_on(self.tenth, hour=8)
        self.visit_on(self.tenth, hour=18)
        response, month = self.last_month()

        self.assertEqual(len(response.context["groups"][0]["rows"]), 2)
        self.assertEqual(sum(1 for cell in self.cells(month) if cell["has_visit"]), 1)

    def test_a_class_day_is_marked_on_top_of_the_visit(self):
        self.visit_on(self.tenth)
        self.class_on(self.tenth)
        _, month = self.last_month()

        cell = self.cell_for(month, 10)
        self.assertTrue(cell["has_visit"])
        self.assertTrue(cell["has_class"])

    def test_a_class_the_member_never_checked_in_for_still_shows(self):
        self.visit_on(self.tenth)
        self.class_on(self.fifteenth)
        _, month = self.last_month()

        cell = self.cell_for(month, 15)
        self.assertTrue(cell["has_class"])
        self.assertFalse(cell["has_visit"])

    def test_days_after_today_are_marked_as_future(self):
        self.visit_on(self.today)
        response = self.client.get(reverse("member_history"))
        month = response.context["calendar_months"][0]

        for cell in self.cells(month):
            self.assertEqual(cell["is_future"], cell["day"] > self.today.day)
        self.assertTrue(self.cell_for(month, self.today.day)["is_today"])

    def test_legend_appears_only_when_a_class_falls_in_a_month_on_screen(self):
        self.visit_on(self.tenth)
        response = self.client.get(reverse("member_history"))
        self.assertFalse(response.context["has_class_days"])
        self.assertNotContains(response, "Ada kelas")

        self.class_on(self.fifteenth)
        response = self.client.get(reverse("member_history"))
        self.assertTrue(response.context["has_class_days"])
        self.assertContains(response, "Ada kelas")

    def test_no_calendar_without_visits(self):
        response = self.client.get(reverse("member_history"))

        self.assertEqual(response.context["groups"], [])
        self.assertEqual(response.context["calendar_months"], [])
        self.assertNotContains(response, 'class="history-cal"')

    def test_calendar_only_on_the_visits_tab(self):
        self.visit_on(self.tenth)
        response = self.client.get(reverse("member_history"), {"tab": "pembayaran"})

        self.assertNotContains(response, 'class="history-cal-week"')


class AccountWaitlistPlaceTest(TestCase):
    """The account page tells a waitlisted member their place in the queue."""

    def setUp(self):
        from classes.models import Class, ClassSchedule, ClassInstance

        self.member = Member.objects.create(
            name="Queued Member",
            email="queued@example.com",
            phone_number="628563000111",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )
        ahead = Member.objects.create(
            name="Ahead Member",
            email="ahead@example.com",
            phone_number="628563000222",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        class_obj = Class.objects.create(
            name="Semi Private", description="Semi private", max_members=1
        )
        tomorrow = timezone.localdate() + timedelta(days=1)
        schedule = ClassSchedule.objects.create(
            class_obj=class_obj,
            day_of_week=tomorrow.weekday(),
            start_time=time(16, 0),
            end_time=time(17, 0),
        )
        self.instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=tomorrow,
            start_time=time(16, 0),
            end_time=time(17, 0),
        )
        self.instance.waitlisted_members.add(ahead)
        self.instance.waitlisted_members.add(self.member)

    def test_place_shown_on_account_page(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

        response = self.client.get(reverse("member_details"))

        booking = response.context["upcoming_waitlisted_classes"][0]
        self.assertEqual(booking.waitlist_place, 2)
        self.assertContains(response, "ke-2")


class MembershipNudgeTest(TestCase):
    """The renew / come-back strip on the account page."""

    def setUp(self):
        self.member = Member.objects.create(
            name="Nudge Member",
            email="nudge@example.com",
            phone_number="628564000111",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def set_expiry(self, days_from_today, **flags):
        if days_from_today is None:
            self.member.active_until = None
        else:
            self.member.active_until = timezone.now() + timedelta(days=days_from_today)
        for field, value in flags.items():
            setattr(self.member, field, value)
        self.member.save()

    def nudge(self):
        response = self.client.get(reverse("member_details"))
        return response, response.context["membership_nudge"]

    def test_warns_a_few_days_before_expiry(self):
        self.set_expiry(3)
        response, nudge = self.nudge()

        self.assertEqual(nudge["level"], "warning")
        self.assertIn("3 hari lagi", nudge["headline"])
        self.assertContains(response, "3 hari lagi")
        self.assertContains(response, "Perpanjang via WhatsApp")

    def test_urgent_the_day_before(self):
        self.set_expiry(1)
        _, nudge = self.nudge()

        self.assertEqual(nudge["level"], "urgent")
        self.assertIn("besok", nudge["headline"])

    def test_urgent_on_the_last_day(self):
        self.set_expiry(0)
        _, nudge = self.nudge()

        self.assertEqual(nudge["level"], "urgent")
        self.assertIn("hari ini", nudge["headline"])

    def test_come_back_message_after_expiry(self):
        self.set_expiry(-5)
        response, nudge = self.nudge()

        self.assertEqual(nudge["level"], "expired")
        self.assertIn("5 hari lalu", nudge["headline"])
        self.assertContains(response, "Aktifkan via WhatsApp")

    def test_quiet_while_the_membership_is_comfortable(self):
        self.set_expiry(20)
        response, nudge = self.nudge()

        self.assertIsNone(nudge)
        self.assertNotContains(response, "membership-nudge")

    def test_quiet_for_long_lapsed_memberships(self):
        self.set_expiry(-120)
        _, nudge = self.nudge()

        self.assertIsNone(nudge)

    def test_quiet_for_members_with_no_membership_date(self):
        self.set_expiry(None)
        _, nudge = self.nudge()

        self.assertIsNone(nudge)

    def test_quiet_for_members_the_admin_handles_manually(self):
        self.set_expiry(2, skip_auto_reminder=True)
        _, nudge = self.nudge()

        self.assertIsNone(nudge)

    def test_boundaries_of_the_nudge_window(self):
        self.set_expiry(7)
        self.assertIsNotNone(self.nudge()[1])

        self.set_expiry(8)
        self.assertIsNone(self.nudge()[1])

        self.set_expiry(-30)
        self.assertIsNotNone(self.nudge()[1])

        self.set_expiry(-31)
        self.assertIsNone(self.nudge()[1])

    def test_whatsapp_message_identifies_the_member(self):
        self.set_expiry(2)
        _, nudge = self.nudge()

        self.assertTrue(nudge["whatsapp_url"].startswith("https://wa.me/628996940908?text="))
        self.assertIn("Nudge%20Member", nudge["whatsapp_url"])
        self.assertIn("628564000111", nudge["whatsapp_url"])


class VisitMilestoneTest(TestCase):
    """Milestone badge and progress bar under the habit tiles on /akun."""

    def setUp(self):
        self.member = Member.objects.create(
            name="Milestone Member",
            email="milestone@example.com",
            phone_number="628561000222",
            gender="F",
            age=30,
            height=160,
            weight=55,
            years_of_working_out="2 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def add_visits(self, count):
        for _ in range(count):
            Visit.objects.create(member=self.member)

    def test_member_with_no_visits_gets_no_milestone(self):
        self.assertIsNone(_visit_milestone(0))

    def test_before_the_first_badge_it_counts_down_to_it(self):
        milestone = _visit_milestone(3)

        self.assertIsNone(milestone["reached"])
        self.assertEqual(milestone["next"], 5)
        self.assertEqual(milestone["remaining"], 2)
        self.assertEqual(milestone["percent"], 60)

    def test_progress_is_measured_inside_the_current_step(self):
        # 60 visits: past 50, chasing 100, so 10 of the 50-visit step is done.
        milestone = _visit_milestone(60)

        self.assertEqual(milestone["reached"], 50)
        self.assertEqual(milestone["next"], 100)
        self.assertEqual(milestone["remaining"], 40)
        self.assertEqual(milestone["percent"], 20)

    def test_landing_exactly_on_a_badge_keeps_a_sliver_of_bar(self):
        milestone = _visit_milestone(50)

        self.assertEqual(milestone["reached"], 50)
        self.assertEqual(milestone["next"], 100)
        self.assertEqual(milestone["percent"], 4)

    def test_past_the_last_badge_there_is_nothing_left_to_chase(self):
        milestone = _visit_milestone(VISIT_MILESTONES[-1] + 12)

        self.assertEqual(milestone["reached"], VISIT_MILESTONES[-1])
        self.assertIsNone(milestone["next"])
        self.assertEqual(milestone["percent"], 100)

    def test_account_page_shows_the_badge_and_the_next_target(self):
        self.add_visits(12)
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertEqual(response.context["visit_milestone"]["reached"], 10)
        self.assertContains(response, "10 kunjungan")
        self.assertContains(response, "13 lagi ke 25")

    def test_nothing_is_rendered_for_a_member_who_never_visited(self):
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertIsNone(response.context["visit_milestone"])
        self.assertNotContains(response, "lagi ke")


class AccountUpcomingClassActionsTest(TestCase):
    """Kalender and Ajak Temen on the member's own upcoming classes.

    Both already existed on the class detail page. A member checking their
    bookings starts on /akun, so the row that lists a booking is where the two
    are actually reached for.
    """

    def setUp(self):
        from classes.models import Class, ClassSchedule, ClassInstance

        self.ClassSchedule = ClassSchedule
        self.ClassInstance = ClassInstance
        self.member = Member.objects.create(
            name="Actions Member",
            email="actions@example.com",
            phone_number="628560000333",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.class_obj = Class.objects.create(
            name="Yoga Pagi", description="Yoga", max_members=10
        )

    def instance_tomorrow(self):
        start = timezone.localtime(timezone.now()) + timedelta(days=1)
        schedule = self.ClassSchedule.objects.create(
            class_obj=self.class_obj,
            day_of_week=start.weekday(),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        return self.ClassInstance.objects.create(
            class_schedule=schedule,
            date=start.date(),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_booked_row_offers_the_calendar_file_and_the_invite(self):
        instance = self.instance_tomorrow()
        instance.booked_members.add(self.member)
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertContains(
            response, reverse("classes:class_calendar", args=[instance.id])
        )
        self.assertContains(response, "Ajak Temen")
        self.assertContains(response, "https://wa.me/?text=")

    def test_waitlisted_row_offers_them_too(self):
        instance = self.instance_tomorrow()
        instance.waitlisted_members.add(self.member)
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertContains(
            response, reverse("classes:class_calendar", args=[instance.id])
        )
        self.assertContains(response, "Kalender")

    def test_invite_names_the_class_and_links_to_it(self):
        instance = self.instance_tomorrow()
        instance.booked_members.add(self.member)
        self.login()

        response = self.client.get(reverse("member_details"))
        share_url = response.context["upcoming_booked_classes"][0].share_url

        self.assertIn(quote("Yuk ikut kelas Yoga Pagi di Mulai Gym"), share_url)
        self.assertIn(quote("jam 08:00"), share_url)
        self.assertIn(
            quote(f"http://testserver/kelas/{instance.id}/"),
            share_url,
        )

    def test_a_member_with_no_bookings_gets_no_action_buttons(self):
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertNotContains(response, "Ajak Temen")
        self.assertNotContains(response, "Kalender")


class WebManifestTest(TestCase):
    """The home-screen manifest, which shipped for a long time as the default
    template: named "MyWebSite" with icon paths pointing at /images/, a folder
    that does not exist. Nothing failed, the icons just never loaded.
    """

    def manifest(self):
        path = finders.find("favicons/site.webmanifest")
        self.assertIsNotNone(path, "site.webmanifest is not in the static files")
        with open(path) as handle:
            return json.load(handle)

    def test_it_is_named_after_the_gym(self):
        manifest = self.manifest()

        self.assertEqual(manifest["name"], "Mulai Gym")
        self.assertEqual(manifest["short_name"], "Mulai Gym")

    def test_every_icon_path_actually_resolves(self):
        icons = self.manifest()["icons"]
        self.assertTrue(icons)

        for icon in icons:
            src = icon["src"]
            self.assertTrue(
                src.startswith(settings.STATIC_URL),
                f"{src} is not under STATIC_URL, so it will 404",
            )
            relative = src[len(settings.STATIC_URL) :]
            self.assertIsNotNone(
                finders.find(relative), f"{src} does not point at a real file"
            )

    def test_it_opens_on_a_page_we_serve(self):
        manifest = self.manifest()

        # resolve() raises Resolver404 on a path no url pattern matches
        self.assertEqual(resolve(manifest["start_url"]).view_name, "member_details")

    def test_account_page_offers_the_install_hint(self):
        member = Member.objects.create(
            name="Install Member",
            email="install@example.com",
            phone_number="628560000555",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        session = self.client.session
        session["member_email"] = member.email
        session.save()

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "Simpan Mulai Gym di HP kamu")
        self.assertContains(response, 'rel="manifest"')


class PaymentRowTest(TestCase):
    """Payment rows on /akun.

    They used to render `payment.duration_choice` and `get_duration_choice_display`,
    neither of which exists on Payment. Django resolves a missing attribute to an
    empty string, so every row carried a blank line where the duration should be.
    """

    def setUp(self):
        self.member = Member.objects.create(
            name="Payment Member",
            email="payments@example.com",
            phone_number="628560000666",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        self.package = Package.objects.create(
            code="0-BRONZE-1",
            default_price=400000,
            description="Gym Reguler 1 bulan",
        )
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_row_names_the_package_that_was_bought(self):
        Payment.objects.create(
            member=self.member,
            package=self.package,
            amount=400000,
            payment_date=timezone.now(),
            payment_method="CASH",
        )

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "Gym Reguler 1 bulan")
        self.assertContains(response, "Rp 400,000")

    def test_installments_are_flagged_and_nothing_else_is(self):
        Payment.objects.create(
            member=self.member,
            package=self.package,
            amount=200000,
            payment_date=timezone.now(),
            payment_method="TRANSFER",
            apakah_nyicil=True,
        )

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "Cicilan")

    def test_a_plain_payment_says_nothing_about_installments(self):
        Payment.objects.create(
            member=self.member,
            package=self.package,
            amount=400000,
            payment_date=timezone.now(),
            payment_method="CASH",
        )

        response = self.client.get(reverse("member_details"))

        self.assertNotContains(response, "Cicilan")


class LocalDateOnTheAccountPageTest(TestCase):
    """Jakarta is UTC+7, so from midnight until 07:00 the UTC date is still
    yesterday. The page used to ask for `timezone.now().date()`, so for those
    seven hours every morning a class from yesterday sat under "Kelas yang Akan
    Datang" and today's history counted the wrong day.
    """

    # 18:30 UTC is 01:30 the next morning in Jakarta, inside the broken window.
    NOW_UTC = datetime(2026, 3, 16, 18, 30, tzinfo=dt_timezone.utc)
    JAKARTA_TODAY = date(2026, 3, 17)

    def setUp(self):
        from classes.models import Class, ClassSchedule

        self.ClassSchedule = ClassSchedule
        self.member = Member.objects.create(
            name="Local Date Member",
            email="localdate@example.com",
            phone_number="628560000777",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )
        self.class_obj = Class.objects.create(
            name="Kelas Pemula", description="Beginner", max_members=10
        )
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def book_on(self, day):
        from classes.models import ClassInstance

        schedule, _ = self.ClassSchedule.objects.get_or_create(
            class_obj=self.class_obj,
            day_of_week=day.weekday(),
            start_time=time(8, 0),
            defaults={"end_time": time(9, 0)},
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=day,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        instance.booked_members.add(self.member)
        return instance

    @patch("django.utils.timezone.now")
    def test_at_half_past_one_in_the_morning_today_is_still_today(self, now):
        now.return_value = self.NOW_UTC
        yesterday = self.book_on(self.JAKARTA_TODAY - timedelta(days=1))
        today = self.book_on(self.JAKARTA_TODAY)

        response = self.client.get(reverse("member_details"))
        upcoming = [b.id for b in response.context["upcoming_booked_classes"]]
        past = [b.id for b in response.context["past_booked_classes"]]

        self.assertEqual(upcoming, [today.id])
        self.assertEqual(past, [yesterday.id])

    @patch("django.utils.timezone.now")
    def test_yesterdays_class_is_not_bookable_at_half_past_one(self, now):
        now.return_value = self.NOW_UTC
        yesterday = self.book_on(self.JAKARTA_TODAY - timedelta(days=1))
        today = self.book_on(self.JAKARTA_TODAY)

        self.assertFalse(yesterday.is_bookable)
        self.assertTrue(today.is_bookable)


class SharedMotionAssetTest(TestCase):
    """The shared motion helper must exist and be reachable.

    A `{% static %}` path that is not in the manifest raises in production
    (CompressedManifestStaticFilesStorage), so a renamed or deleted file would
    take every member page down rather than quietly dropping the animation.
    """

    def test_the_helper_file_is_there(self):
        self.assertIsNotNone(finders.find("js/mulai.js"))

    def test_every_page_loads_it(self):
        member = Member.objects.create(
            name="Motion Member",
            email="motion@example.com",
            phone_number="628560000999",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
        )
        session = self.client.session
        session["member_email"] = member.email
        session.save()

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "js/mulai.js")
        # The class that hides a revealing card is only ever added by script, so
        # a browser without JS renders everything.
        self.assertNotContains(response, 'class="mg-js"')

    def test_it_claims_mg_ready_so_the_fallback_does_not_fire(self):
        path = finders.find("js/mulai.js")
        with open(path) as handle:
            source = handle.read()

        self.assertIn("window.mgReady = true", source)
        self.assertIn("prefers-reduced-motion", source)
