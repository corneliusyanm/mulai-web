from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.urls import reverse
from unittest.mock import Mock

from .models import Member, Tamu, Masukkan, Prospect
from .admin import ProspectAdmin, MemberAdmin, SaleInline
from .models import User
from visits.admin import admin_site
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
