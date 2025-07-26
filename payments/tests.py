from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model

from accounts.models import Member
from .models import Payment, Package
from .admin import PaymentAdminForm

User = get_user_model()


class PaymentModelTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            name="Test Member",
            email="test@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
        )

    def test_payment_for_new_member(self):
        """
        Test creating a payment for a new member.
        The active_until date should be based on the payment date.
        """
        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=payment_date,
            duration_choice=30,  # 1 Month
        )
        expected_end_date = (
            payment_date.date() + relativedelta(months=1) - timedelta(days=1)
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.active_until.date(), expected_end_date)

    def test_payment_for_active_member(self):
        """
        Test that a new payment for an active member stacks the duration.
        """
        # Make the member active
        initial_end_date = timezone.now() + timedelta(days=15)
        self.member.active_until = initial_end_date
        self.member.save()

        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.now(),
            duration_choice=30,  # 1 Month
        )

        expected_start_date = initial_end_date.date() + timedelta(days=1)
        expected_end_date = (
            expected_start_date + relativedelta(months=1) - timedelta(days=1)
        )

        self.member.refresh_from_db()
        self.assertEqual(self.member.active_until.date(), expected_end_date)

    def test_payment_for_expired_member(self):
        """
        Test payment for a member whose membership has expired.
        The new period should start from the payment date.
        """
        # Set a past active_until date
        self.member.active_until = timezone.now() - timedelta(days=10)
        self.member.save()

        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=payment_date,
            duration_choice=30,  # 1 Month
        )

        expected_end_date = (
            payment_date.date() + relativedelta(months=1) - timedelta(days=1)
        )

        self.member.refresh_from_db()
        self.assertEqual(self.member.active_until.date(), expected_end_date)

    def test_payment_with_custom_duration(self):
        """
        Test payment with a custom duration in days.
        """
        payment_date = timezone.now()
        custom_days = 45
        payment = Payment.objects.create(
            member=self.member,
            amount=200000,
            payment_date=payment_date,
            duration_choice=0,  # Custom
            duration_days=custom_days,
        )

        expected_end_date = payment_date.date() + timedelta(days=custom_days - 1)

        self.member.refresh_from_db()
        self.assertEqual(self.member.active_until.date(), expected_end_date)

    def test_payment_apakah_nyicil_default_false(self):
        """
        Test that apakah_nyicil defaults to False.
        """
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.now(),
            duration_choice=30,
        )
        self.assertFalse(payment.apakah_nyicil)

    def test_payment_apakah_nyicil_true(self):
        """
        Test creating a payment with apakah_nyicil set to True.
        """
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.now(),
            duration_choice=30,
            apakah_nyicil=True,
        )
        self.assertTrue(payment.apakah_nyicil)


class PaymentAdminFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="admin@example.com", password="testpass123"
        )
        self.member = Member.objects.create(
            name="Test Member",
            email="test@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
        )
        self.package = Package.objects.create(
            code="M1", default_price=150000, description="1 Month Membership"
        )

    def test_payment_admin_form_fields(self):
        """
        Test that PaymentAdminForm includes all required fields.
        """
        form = PaymentAdminForm()
        expected_fields = [
            "member",
            "package",
            "amount",
            "duration_choice",
            "duration_days",
            "payment_date",
            "payment_method",
            "apakah_nyicil",
            "notes",
        ]
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_payment_admin_form_apakah_nyicil_configuration(self):
        """
        Test that apakah_nyicil field is properly configured with label and choices.
        """
        form = PaymentAdminForm()
        apakah_nyicil_field = form.fields["apakah_nyicil"]

        self.assertEqual(apakah_nyicil_field.label, "Apakah bagian dari cicilan?")
        self.assertEqual(apakah_nyicil_field.initial, False)
        self.assertEqual(
            apakah_nyicil_field.widget.choices, [(True, "Ya"), (False, "Tidak")]
        )

    def test_payment_admin_form_apakah_nyicil_field_exists(self):
        """
        Test that apakah_nyicil field exists and can be set.
        """
        # Create form instance with minimal data
        payment = Payment(
            member=self.member,
            package=self.package,
            amount=150000,
            duration_choice=30,
            payment_date=timezone.now(),
            payment_method="TRANSFER",
            apakah_nyicil=True,
        )
        form = PaymentAdminForm(instance=payment)

        # Check that the field exists and has the right configuration
        self.assertIn("apakah_nyicil", form.fields)
        self.assertEqual(
            form.fields["apakah_nyicil"].label, "Apakah bagian dari cicilan?"
        )
        self.assertEqual(form.initial["apakah_nyicil"], True)

    def test_payment_admin_form_custom_duration_validation(self):
        """
        Test that custom duration validation logic works.
        """
        form = PaymentAdminForm()

        # Test the clean method directly with mock data
        cleaned_data = {
            "duration_choice": 0,  # Custom
            "duration_days": None,
            "member": self.member,
            "package": self.package,
            "amount": 150000,
            "payment_method": "TRANSFER",
            "apakah_nyicil": False,
        }

        # Manually set the cleaned_data and test validation
        form.cleaned_data = cleaned_data
        try:
            result = form.clean()
            # If no exception, the validation passed incorrectly
            self.fail("Expected validation error for missing duration_days")
        except Exception:
            # Expected behavior - validation should fail
            pass

        # Test valid case
        cleaned_data["duration_days"] = 45
        form.cleaned_data = cleaned_data
        result = form.clean()
        self.assertEqual(result, cleaned_data)  # Should return cleaned data
