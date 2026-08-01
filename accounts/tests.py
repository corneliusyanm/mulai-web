from datetime import timedelta, time

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.urls import reverse
from unittest.mock import Mock

from .models import Member, ActiveMember, Tamu, Masukkan, Prospect
from .admin import ProspectAdmin, MemberAdmin, ActiveMemberAdmin, SaleInline
from .models import User
from visits.admin import admin_site
from visits.models import Visit
from payments.models import Payment
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
        self.assertEqual(upcoming_booked.count(), 2)
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
        self.assertEqual(upcoming_waitlisted.count(), 1)
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
        self.assertEqual(response.context["upcoming_booked_classes"].count(), 0)
        self.assertEqual(response.context["past_booked_classes"].count(), 0)
        self.assertEqual(response.context["upcoming_waitlisted_classes"].count(), 0)
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
