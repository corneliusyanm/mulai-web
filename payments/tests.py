from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from accounts.models import Member
from .models import Payment


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
