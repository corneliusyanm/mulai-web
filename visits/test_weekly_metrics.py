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

    def test_new_members_section(self):
        """Test that new members (first membership package payments) are correctly identified"""
        # Create a new member who makes their first membership package payment
        new_member = Member.objects.create(
            name="Andi",
            email="andi@test.com",
            phone_number="6281111111116",
            gender="M",
            age=26,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Weight loss",
            know_mulai_gym_from="Facebook",
            why_choose_mulai="Good facilities",
            address="Jakarta",
            is_pemula=True,
        )

        # Create a single-visit package (should be excluded)
        single_visit_package = Package.objects.create(
            code="0-BRONZE-0",
            default_price=50000,
            description="Single visit pass",
        )

        # Andi makes a single-visit payment first (should not count as new member)
        self.create_weekly_payment(
            new_member,
            single_visit_package,
            date(2025, 9, 14),
            notes="Single visit",
        )

        # Then Andi makes his first membership package payment (should count as new member)
        self.create_weekly_payment(
            new_member,
            self.silver_3_months,
            date(2025, 9, 15),
            notes="First membership package",
        )

        # Create another member who had previous membership payments before
        existing_member = Member.objects.create(
            name="Budi",
            email="budi@test.com",
            phone_number="6281111111117",
            gender="M",
            age=30,
            height=170,
            weight=65,
            years_of_working_out="2 years",
            goals="Fitness",
            know_mulai_gym_from="Friends",
            why_choose_mulai="Good trainer",
            address="Bandung",
            is_pemula=False,
        )

        # Budi had a previous membership payment before the test week
        Payment.objects.create(
            member=existing_member,
            package=self.bronze_1_month,
            amount=self.bronze_1_month.default_price,
            payment_date=timezone.make_aware(datetime(2025, 8, 1, 10, 0, 0)),
        )

        # Budi makes another payment during test week (should not count as new member)
        self.create_weekly_payment(
            existing_member,
            self.bronze_3_months,
            date(2025, 9, 16),
            notes="Renewal payment",
        )

        # Use Django test client
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check new members
        new_members = context.get("new_members_payments", [])
        self.assertEqual(len(new_members), 1)
        
        # Should be Andi (the one who made first membership package payment)
        self.assertEqual(new_members[0]["member"].name, "Andi")
        self.assertEqual(new_members[0]["package_code"], "1-SILVER-3")
        self.assertEqual(new_members[0]["payment_amount"], self.silver_3_months.default_price)
        self.assertEqual(new_members[0]["payment_note"], "First membership package")
        self.assertEqual(new_members[0]["is_pemula"], True)
        self.assertEqual(new_members[0]["address"], "Jakarta")
        self.assertEqual(new_members[0]["goals"], "Weight loss")
        self.assertEqual(new_members[0]["know_mulai_gym_from"], "Facebook")
        self.assertEqual(new_members[0]["why_choose_mulai"], "Good facilities")

        # Budi should not be in new members (he had previous membership payments)
        new_member_names = [nm["member"].name for nm in new_members]
        self.assertNotIn("Budi", new_member_names)

    def test_new_members_excludes_single_visit_packages(self):
        """Test that single-visit packages (*-0) are excluded from new members calculation"""
        # Create a new member who only buys single-visit passes
        single_visit_only_member = Member.objects.create(
            name="Citra",
            email="citra@test.com",
            phone_number="6281111111118",
            gender="F",
            age=24,
            height=165,
            weight=55,
            years_of_working_out="Beginner",
            goals="Try gym",
            know_mulai_gym_from="Instagram",
        )

        # Create single-visit package
        single_visit_package = Package.objects.create(
            code="0-BRONZE-0",
            default_price=50000,
            description="Single visit pass",
        )

        # Citra only buys single-visit passes during the week
        self.create_weekly_payment(
            single_visit_only_member,
            single_visit_package,
            date(2025, 9, 14),
            notes="Single visit 1",
        )
        
        self.create_weekly_payment(
            single_visit_only_member,
            single_visit_package,
            date(2025, 9, 16),
            notes="Single visit 2",
        )

        # Use Django test client
        from django.test import Client

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Should have no new members (single-visit passes don't count)
        new_members = context.get("new_members_payments", [])
        self.assertEqual(len(new_members), 0)

    def test_referral_source_breakdown_with_mixed_sources(self):
        """Test that referral source breakdown correctly normalizes and counts mixed source values"""
        from django.test import Client

        # Create new members with various referral sources
        member1 = Member.objects.create(
            name="User1",
            email="user1@test.com",
            phone_number="6281111111119",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="Beginner",
            goals="Fitness",
            know_mulai_gym_from="ig",  # Should normalize to "Instagram"
        )

        member2 = Member.objects.create(
            name="User2",
            email="user2@test.com",
            phone_number="6281111111120",
            gender="F",
            age=26,
            height=165,
            weight=55,
            years_of_working_out="Beginner",
            goals="Health",
            know_mulai_gym_from="Instagram",  # Should normalize to "Instagram"
        )

        member3 = Member.objects.create(
            name="User3",
            email="user3@test.com",
            phone_number="6281111111121",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="insta",  # Should normalize to "Instagram"
        )

        member4 = Member.objects.create(
            name="User4",
            email="user4@test.com",
            phone_number="6281111111122",
            gender="F",
            age=24,
            height=160,
            weight=50,
            years_of_working_out="Beginner",
            goals="Weight loss",
            know_mulai_gym_from="tik tok",  # Should normalize to "TikTok"
        )

        member5 = Member.objects.create(
            name="User5",
            email="user5@test.com",
            phone_number="6281111111123",
            gender="M",
            age=28,
            height=180,
            weight=75,
            years_of_working_out="Beginner",
            goals="Strength",
            know_mulai_gym_from="teman",  # Should normalize to "Referral / Friend"
        )

        # Create first membership package payments for all members during test week
        for member in [member1, member2, member3, member4, member5]:
            self.create_weekly_payment(
                member,
                self.silver_3_months,
                date(2025, 9, 15),
            )

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check referral source breakdown
        breakdown = context.get("referral_source_breakdown", [])
        
        # Should have 3 unique sources after normalization: Instagram (3), TikTok (1), Referral / Friend (1)
        self.assertEqual(len(breakdown), 3)
        
        # Check Instagram count (should be 3: ig, Instagram, insta)
        instagram_entry = next((item for item in breakdown if item["source"] == "Instagram"), None)
        self.assertIsNotNone(instagram_entry)
        self.assertEqual(instagram_entry["count"], 3)
        
        # Check TikTok count (should be 1: tik tok)
        tiktok_entry = next((item for item in breakdown if item["source"] == "TikTok"), None)
        self.assertIsNotNone(tiktok_entry)
        self.assertEqual(tiktok_entry["count"], 1)
        
        # Check Referral / Friend count (should be 1: teman)
        friend_entry = next((item for item in breakdown if item["source"] == "Referral / Friend"), None)
        self.assertIsNotNone(friend_entry)
        self.assertEqual(friend_entry["count"], 1)

    def test_referral_source_breakdown_empty_null_grouped(self):
        """Test that empty/null/whitespace sources are grouped under '(Tidak diisi)'"""
        from django.test import Client

        # Create members with empty/null referral sources
        member1 = Member.objects.create(
            name="User1",
            email="user1@test.com",
            phone_number="6281111111124",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="Beginner",
            goals="Fitness",
            know_mulai_gym_from="",  # Empty string
        )

        member2 = Member.objects.create(
            name="User2",
            email="user2@test.com",
            phone_number="6281111111125",
            gender="F",
            age=26,
            height=165,
            weight=55,
            years_of_working_out="Beginner",
            goals="Health",
            know_mulai_gym_from="",  # Empty string (field doesn't allow NULL)
        )

        member3 = Member.objects.create(
            name="User3",
            email="user3@test.com",
            phone_number="6281111111126",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="   ",  # Whitespace only
        )

        member3b = Member.objects.create(
            name="User3b",
            email="user3b@test.com",
            phone_number="6281111111131",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="-",  # Placeholder
        )

        member3c = Member.objects.create(
            name="User3c",
            email="user3c@test.com",
            phone_number="6281111111132",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="_",  # Placeholder
        )

        member3d = Member.objects.create(
            name="User3d",
            email="user3d@test.com",
            phone_number="6281111111133",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="n/a",  # Placeholder
        )

        member4 = Member.objects.create(
            name="User4",
            email="user4@test.com",
            phone_number="6281111111127",
            gender="F",
            age=24,
            height=160,
            weight=50,
            years_of_working_out="Beginner",
            goals="Weight loss",
            know_mulai_gym_from="Instagram",  # Valid source
        )

        # Create first membership package payments for all members during test week
        for member in [member1, member2, member3, member3b, member3c, member3d, member4]:
            self.create_weekly_payment(
                member,
                self.silver_3_months,
                date(2025, 9, 15),
            )

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check referral source breakdown
        breakdown = context.get("referral_source_breakdown", [])
        
        # Should have 2 unique sources: "(Tidak diisi)" (6) and "Instagram" (1)
        self.assertEqual(len(breakdown), 2)
        
        # Check "(Tidak diisi)" count (should be 6: empty, None, whitespace, -, _, n/a)
        not_filled_entry = next((item for item in breakdown if item["source"] == "(Tidak diisi)"), None)
        self.assertIsNotNone(not_filled_entry)
        self.assertEqual(not_filled_entry["count"], 6)

    def test_referral_source_breakdown_ignores_outside_date_range(self):
        """Test that members whose first qualifying payment falls outside date range are ignored"""
        from django.test import Client

        # Create a member with payment BEFORE the test week
        member_before = Member.objects.create(
            name="BeforeMember",
            email="before@test.com",
            phone_number="6281111111128",
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="Beginner",
            goals="Fitness",
            know_mulai_gym_from="Instagram",
        )

        # Create payment BEFORE test week (Sept 10, outside Sept 13-19 range)
        self.create_weekly_payment(
            member_before,
            self.silver_3_months,
            date(2025, 9, 10),
        )

        # Create a member with payment AFTER the test week
        member_after = Member.objects.create(
            name="AfterMember",
            email="after@test.com",
            phone_number="6281111111129",
            gender="F",
            age=26,
            height=165,
            weight=55,
            years_of_working_out="Beginner",
            goals="Health",
            know_mulai_gym_from="TikTok",
        )

        # Create payment AFTER test week (Sept 20, outside Sept 13-19 range)
        self.create_weekly_payment(
            member_after,
            self.silver_3_months,
            date(2025, 9, 20),
        )

        # Create a member with payment DURING the test week
        member_during = Member.objects.create(
            name="DuringMember",
            email="during@test.com",
            phone_number="6281111111130",
            gender="M",
            age=27,
            height=175,
            weight=70,
            years_of_working_out="Beginner",
            goals="Muscle",
            know_mulai_gym_from="Friend",
        )

        # Create payment DURING test week (Sept 15, inside Sept 13-19 range)
        self.create_weekly_payment(
            member_during,
            self.silver_3_months,
            date(2025, 9, 15),
        )

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check referral source breakdown
        breakdown = context.get("referral_source_breakdown", [])
        
        # Should only have 1 source: "Referral / Friend" (from member_during)
        # The before and after members should be excluded
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["source"], "Referral / Friend")
        self.assertEqual(breakdown[0]["count"], 1)

    def test_referral_source_breakdown_percentages_sum_to_100(self):
        """Test that percentages in referral source breakdown sum to 100 (within rounding tolerance)"""
        from django.test import Client

        # Create new members with different referral sources
        members_data = [
            ("User1", "Instagram"),
            ("User2", "TikTok"),
            ("User3", "Friend"),
            ("User4", "Google"),
            ("User5", "Instagram"),  # Duplicate source
        ]

        for i, (name, source) in enumerate(members_data):
            member = Member.objects.create(
                name=name,
                email=f"user{i+1}@test.com",
                phone_number=f"628111111113{i+1}",
                gender="M",
                age=25 + i,
                height=170,
                weight=65,
                years_of_working_out="Beginner",
                goals="Fitness",
                know_mulai_gym_from=source,
            )
            self.create_weekly_payment(
                member,
                self.silver_3_months,
                date(2025, 9, 15),
            )

        client = Client()
        client.force_login(self.staff_user)

        response = client.get(
            "/admin/analytics/weekly-metrics/",
            {"start_date": "2025-09-13", "end_date": "2025-09-19"},
        )
        context = response.context

        # Check referral source breakdown
        breakdown = context.get("referral_source_breakdown", [])
        
        # Sum all percentages
        total_percentage = sum(item["percentage"] for item in breakdown)
        
        # Should be approximately 100 (within 0.1 tolerance for rounding)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
