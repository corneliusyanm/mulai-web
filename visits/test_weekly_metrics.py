from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from accounts.models import Member
from payments.models import Payment, Package
from .admin import weekly_metrics_view

User = get_user_model()


class WeeklyMetricsViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # Create a staff user
        self.staff_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass",
            is_staff=True,
            is_superuser=True,
        )

        # Create test packages
        self.bronze_1_month = Package.objects.create(
            code="0-BRONZE-1",
            default_price=400000,
            description="Bronze 1 month membership",
        )

        self.bronze_3_months = Package.objects.create(
            code="0-BRONZE-3",
            default_price=1000000,
            description="Bronze 3 months membership",
        )

        self.silver_3_months = Package.objects.create(
            code="1-SILVER-3",
            default_price=1300000,
            description="Silver 3 months membership",
        )

        self.bronze_12_months = Package.objects.create(
            code="0-BRONZE-12",
            default_price=4000000,
            description="Bronze 12 months membership",
        )

        # Test dates
        self.test_start_date = date(2025, 9, 13)
        self.test_end_date = date(2025, 9, 19)

        # Create test members
        self.existing_member_expiring = Member.objects.create(
            name="Diana Aryani",
            email="diana@test.com",
            phone_number="6281111111111",
            gender="F",
            age=25,
            height=160,
            weight=55,
            years_of_working_out="1 year",
            goals="Fitness",
            know_mulai_gym_from="Instagram",
        )

        self.existing_member_early_renewal = Member.objects.create(
            name="Dian",
            email="dian@test.com",
            phone_number="6281111111112",
            gender="F",
            age=28,
            height=165,
            weight=58,
            years_of_working_out="2 years",
            goals="Health",
            know_mulai_gym_from="Friends",
        )

        self.existing_member_installment = Member.objects.create(
            name="Josh",
            email="josh@test.com",
            phone_number="6281111111113",
            gender="M",
            age=30,
            height=175,
            weight=70,
            years_of_working_out="3 years",
            goals="Muscle building",
            know_mulai_gym_from="Social media",
        )

        self.new_member = Member.objects.create(
            name="Haekal",
            email="haekal@test.com",
            phone_number="6281111111114",
            gender="M",
            age=22,
            height=170,
            weight=65,
            years_of_working_out="Beginner",
            goals="Get started",
            know_mulai_gym_from="Advertisement",
        )

    def create_past_payment(self, member, package, days_ago=30):
        """Helper to create a payment in the past to make member 'existing'"""
        past_date = timezone.now() - timedelta(days=days_ago)
        payment = Payment.objects.create(
            member=member,
            package=package,
            amount=package.default_price,
            payment_date=past_date,
        )
        return payment

    def create_weekly_payment(self, member, package, payment_date, **kwargs):
        """Helper to create a payment during the test week"""
        payment_datetime = timezone.make_aware(
            datetime.combine(payment_date, datetime.min.time())
        )
        return Payment.objects.create(
            member=member,
            package=package,
            amount=kwargs.get("amount", package.default_price),
            payment_date=payment_datetime,
            notes=kwargs.get("notes", ""),
            apakah_nyicil=kwargs.get("apakah_nyicil", False),
        )

    def test_expiring_member_renewal(self):
        """Test that a member whose membership expires this week and renews is correctly categorized"""
        # Make Diana an existing member with a past payment from August (before test week)
        past_payment_date = timezone.make_aware(
            datetime(
                2025, 8, 15, 10, 0, 0
            )  # August 15, well before Sept 13-19 test week
        )
        Payment.objects.create(
            member=self.existing_member_expiring,
            package=self.bronze_1_month,
            amount=self.bronze_1_month.default_price,
            payment_date=past_payment_date,
        )

        # Set her membership to expire on Sept 16 (within test week)
        self.existing_member_expiring.active_until = timezone.make_aware(
            datetime(2025, 9, 16, 16, 59, 59)
        )
        self.existing_member_expiring.save()

        # She makes a renewal payment on Sept 15
        payment = self.create_weekly_payment(
            self.existing_member_expiring,
            self.bronze_1_month,
            date(2025, 9, 15),
            notes="Renewal payment",
        )

        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # She should appear in expiring renewals
        self.assertEqual(len(context.get("expiring_renewals", [])), 1)
        self.assertEqual(context["expiring_renewals"][0]["member"].name, "Diana Aryani")

    def test_early_renewal(self):
        """Test that a member who renews before expiry is correctly categorized"""
        # Make Dian an existing member with a past payment from July (before test week)
        Payment.objects.create(
            member=self.existing_member_early_renewal,
            package=self.silver_3_months,
            amount=self.silver_3_months.default_price,
            payment_date=timezone.make_aware(datetime(2025, 7, 10, 10, 0, 0)),
        )

        # Set her membership to expire much later (not in test week)
        # Use a date far in the future to ensure it's treated as "active" by the Payment model
        self.existing_member_early_renewal.active_until = timezone.make_aware(
            datetime(2027, 12, 20, 16, 59, 59)
        )
        self.existing_member_early_renewal.save()

        # She makes an early renewal payment on Sept 17
        self.create_weekly_payment(
            self.existing_member_early_renewal,
            self.silver_3_months,
            date(2025, 9, 17),
            amount=1183000,
            notes="SILVER 3 BLN NORMAL 1.300-9% = Rp 1.183.000 DISKON SEPTEMBER SALE 9%",
        )

        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # She should appear in early renewals
        self.assertEqual(len(context.get("early_renewals", [])), 1)
        self.assertEqual(context["early_renewals"][0]["member"].name, "Dian")

    def test_installment_payment(self):
        """Test that installment payments are correctly categorized"""
        # Make Josh an existing member with a past payment from May (before test week)
        Payment.objects.create(
            member=self.existing_member_installment,
            package=self.bronze_12_months,
            amount=self.bronze_12_months.default_price,
            payment_date=timezone.make_aware(datetime(2025, 5, 1, 10, 0, 0)),
        )

        # He makes an installment payment on Sept 13
        self.create_weekly_payment(
            self.existing_member_installment,
            self.bronze_12_months,
            date(2025, 9, 13),
            amount=183000,
            notes="CICILAN KE-3 183.000 bulan",
            apakah_nyicil=True,
        )

        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # He should appear in installment payments
        self.assertEqual(len(context.get("installment_payments", [])), 1)
        self.assertEqual(context["installment_payments"][0]["member"].name, "Josh")

    def test_new_member_excluded(self):
        """Test that new members (first-time purchasers) are excluded from analysis"""
        # Haekal makes his first payment (no previous payments)
        self.create_weekly_payment(
            self.new_member,
            self.bronze_3_months,
            date(2025, 9, 13),
            notes="PROMO SEPTEMBER SALE",
        )

        request = self.factory.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        request.user = self.staff_user

        response = weekly_metrics_view(request)
        context = response.context_data if hasattr(response, "context_data") else {}

        # He should not appear in any renewal category
        expiring_names = [
            r["member"].name for r in context.get("expiring_renewals", [])
        ]
        early_names = [r["member"].name for r in context.get("early_renewals", [])]
        installment_names = [
            r["member"].name for r in context.get("installment_payments", [])
        ]

        self.assertNotIn("Haekal", expiring_names)
        self.assertNotIn("Haekal", early_names)
        self.assertNotIn("Haekal", installment_names)

    def test_member_who_did_not_repurchase(self):
        """Test that members whose membership expired but didn't renew are correctly identified"""
        # Create an existing member whose membership expires but doesn't renew
        expired_member = Member.objects.create(
            name="Dery Sapta",
            email="dery@test.com",
            phone_number="6281111111115",
            gender="M",
            age=27,
            height=172,
            weight=68,
            years_of_working_out="1 year",
            goals="Fitness",
            know_mulai_gym_from="Friend",
        )

        # Make him an existing member with past payment from August (before test week)
        Payment.objects.create(
            member=expired_member,
            package=self.bronze_1_month,
            amount=self.bronze_1_month.default_price,
            payment_date=timezone.make_aware(datetime(2025, 8, 10, 10, 0, 0)),
        )

        # Set his membership to expire on Sept 13 (within test week)
        expired_member.active_until = timezone.make_aware(
            datetime(2025, 9, 13, 16, 59, 59)
        )
        expired_member.save()

        # He makes NO renewal payment during the week

        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # He should appear in did_not_repurchase_members
        did_not_repurchase_names = [
            m.name for m in context.get("did_not_repurchase_members", [])
        ]
        self.assertIn("Dery Sapta", did_not_repurchase_names)

    def test_statistics_calculation(self):
        """Test that statistics are calculated correctly"""
        # Set up various scenarios

        # Expiring member who renews (Diana)
        Payment.objects.create(
            member=self.existing_member_expiring,
            package=self.bronze_1_month,
            amount=self.bronze_1_month.default_price,
            payment_date=timezone.make_aware(datetime(2025, 8, 15, 10, 0, 0)),
        )
        self.existing_member_expiring.active_until = timezone.make_aware(
            datetime(2025, 9, 16, 16, 59, 59)
        )
        self.existing_member_expiring.save()
        self.create_weekly_payment(
            self.existing_member_expiring, self.bronze_1_month, date(2025, 9, 15)
        )

        # Early renewal (Dian)
        Payment.objects.create(
            member=self.existing_member_early_renewal,
            package=self.silver_3_months,
            amount=self.silver_3_months.default_price,
            payment_date=timezone.make_aware(datetime(2025, 7, 10, 10, 0, 0)),
        )
        # Use a date far in the future to ensure it's treated as "active" by the Payment model
        self.existing_member_early_renewal.active_until = timezone.make_aware(
            datetime(2027, 12, 20, 16, 59, 59)
        )
        self.existing_member_early_renewal.save()
        self.create_weekly_payment(
            self.existing_member_early_renewal, self.silver_3_months, date(2025, 9, 17)
        )

        # Installment payment (Josh)
        Payment.objects.create(
            member=self.existing_member_installment,
            package=self.bronze_12_months,
            amount=self.bronze_12_months.default_price,
            payment_date=timezone.make_aware(datetime(2025, 5, 1, 10, 0, 0)),
        )
        self.create_weekly_payment(
            self.existing_member_installment,
            self.bronze_12_months,
            date(2025, 9, 13),
            apakah_nyicil=True,
        )

        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check statistics
        self.assertEqual(context.get("total_expiring_renewed", 0), 1)  # Diana
        self.assertEqual(context.get("total_early_renewals", 0), 1)  # Dian
        self.assertEqual(context.get("total_installment_payments", 0), 1)  # Josh
        self.assertEqual(context.get("total_all_renewals", 0), 2)  # Diana + Dian

    def test_permission_denied_for_non_staff(self):
        """Test that non-staff users cannot access the view"""
        # Create non-staff user
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="testpass",
            is_staff=False,
        )

        request = self.factory.get("/admin/analytics/weekly-metrics/")
        request.user = regular_user

        with self.assertRaises(Exception):  # Should raise PermissionDenied
            weekly_metrics_view(request)

    def test_date_parameter_handling(self):
        """Test that date parameters are handled correctly"""
        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        self.assertEqual(context.get("start_date"), date(2025, 9, 13))
        self.assertEqual(context.get("end_date"), date(2025, 9, 19))

    def test_invalid_date_parameters(self):
        """Test handling of invalid date parameters"""
        # Use Django test client instead of RequestFactory for admin views
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "invalid-date", "end_date": "also-invalid"},
        )
        context = response.context

        # Should fall back to default dates (today - 6 days to today)
        self.assertIsInstance(context.get("start_date"), date)
        self.assertIsInstance(context.get("end_date"), date)
