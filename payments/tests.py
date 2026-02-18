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

    def test_payment_for_new_member_without_package(self):
        """
        Test creating a payment for a new member without package.
        Should NOT auto-update membership - admin handles manually.
        """
        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=payment_date,
        )
        self.member.refresh_from_db()
        # No package = no auto-update, admin handles manually
        self.assertIsNone(self.member.active_until)

    def test_payment_for_active_member_without_package(self):
        """
        Test that a payment without package for an active member doesn't auto-update.
        """
        # Make the member active
        initial_end_date = timezone.now() + timedelta(days=15)
        self.member.active_until = initial_end_date
        self.member.save()

        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        # Should remain unchanged - no auto-update without package
        self.assertEqual(self.member.active_until, initial_end_date)

    def test_payment_for_expired_member_without_package(self):
        """
        Test payment for a member whose membership has expired without package.
        Should NOT auto-update - admin handles manually.
        """
        # Set a past active_until date
        expired_date = timezone.now() - timedelta(days=10)
        self.member.active_until = expired_date
        self.member.save()

        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=payment_date,
        )

        self.member.refresh_from_db()
        # Should remain expired - no auto-update without package
        self.assertEqual(self.member.active_until, expired_date)

    def test_payment_without_package_no_auto_update(self):
        """
        Test payment without package doesn't auto-update membership.
        """
        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            amount=200000,
            payment_date=payment_date,
        )

        self.member.refresh_from_db()
        # No package = no auto-update, admin handles manually
        self.assertIsNone(self.member.active_until)
        # Payment should have membership_end_date set for tracking
        self.assertEqual(payment.membership_end_date.date(), payment_date.date())

    def test_payment_apakah_nyicil_default_false(self):
        """
        Test that apakah_nyicil defaults to False.
        """
        payment = Payment.objects.create(
            member=self.member,
            amount=150000,
            payment_date=timezone.now(),
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
            code="0-BRONZE-1", default_price=150000, description="1 Month Membership"
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
            "payment_date",
            "payment_method",
            "apakah_nyicil",
            "skip_membership_update",
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

    def test_payment_admin_form_skip_membership_update_configuration(self):
        """
        Test that skip_membership_update field is properly configured.
        """
        form = PaymentAdminForm()
        skip_field = form.fields["skip_membership_update"]

        self.assertEqual(skip_field.label, "Skip otomatis update membership?")
        self.assertEqual(
            skip_field.help_text, "Jika Ya, admin harus update membership secara manual"
        )
        self.assertEqual(skip_field.initial, False)
        self.assertEqual(skip_field.widget.choices, [(True, "Ya"), (False, "Tidak")])

    def test_cicilan_forces_skip_membership_update_disabled(self):
        """When apakah_nyicil=Ya, skip_membership_update is auto Ya and non-editable."""
        payment = Payment(
            member=self.member,
            package=self.package,
            amount=150000,
            payment_date=timezone.now(),
            apakah_nyicil=True,
        )
        form = PaymentAdminForm(instance=payment)
        skip_field = form.fields["skip_membership_update"]

        self.assertTrue(skip_field.disabled)
        self.assertEqual(skip_field.initial, True)

    def test_cicilan_form_clean_forces_skip_membership_update(self):
        """Form clean() forces skip_membership_update=True when cicilan."""
        now = timezone.now()
        form = PaymentAdminForm(
            data={
                "member": self.member.id,
                "package": self.package.id,
                "amount": 150000,
                "payment_date_0": now.strftime("%Y-%m-%d"),
                "payment_date_1": now.strftime("%H:%M"),
                "payment_method": "TRANSFER",
                "apakah_nyicil": True,
                "skip_membership_update": False,
                "notes": "",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["skip_membership_update"])


class PackageBasedPaymentTest(TestCase):
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

        # Create test packages
        self.bronze_1_month = Package.objects.create(
            code="0-BRONZE-1", default_price=400000, description="Gym Reguler 1 bulan"
        )
        self.silver_3_months = Package.objects.create(
            code="1-SILVER-3",
            default_price=1750000,
            description="Gym + Kelas Pemula 3 bulan",
        )
        self.gold_6_months = Package.objects.create(
            code="2-GOLD-6",
            default_price=4380000,
            description="Gym + Semi Private 6 bulan",
        )
        self.platinum_1_month = Package.objects.create(
            code="3-PLATINUM-1",
            default_price=930000,
            description="Gym + All In 1 bulan",
        )
        self.diamond_2_months = Package.objects.create(
            code="4-DIAMOND-2",
            default_price=3070000,
            description="Gym + PT 1on1 2 bulan",
        )
        self.add_silver_1_month = Package.objects.create(
            code="5-ADD-SILVER-1",
            default_price=300000,
            description="Kelas Pemula aja 1 bulan",
        )
        self.add_gold_3_months = Package.objects.create(
            code="5-ADD-GOLD-3",
            default_price=1500000,
            description="Kelas Semi Private aja 3 bulan",
        )
        self.bronze_1_day = Package.objects.create(
            code="0-BRONZE-0", default_price=75000, description="Gym Reguler 1x visit"
        )

    def test_parse_package_code(self):
        """Test package code parsing functionality"""
        payment = Payment(package=self.bronze_1_month)
        type_num, level, duration = payment.parse_package_code()
        self.assertEqual(type_num, "0")
        self.assertEqual(level, "BRONZE")
        self.assertEqual(duration, "1")

        payment = Payment(package=self.add_silver_1_month)
        type_num, level, duration = payment.parse_package_code()
        self.assertEqual(type_num, "5")
        self.assertEqual(level, "ADD-SILVER")
        self.assertEqual(duration, "1")

    def test_get_duration_from_package(self):
        """Test duration extraction from package codes"""
        payment = Payment(package=self.bronze_1_month)
        duration = payment.get_duration_from_package()
        self.assertEqual(duration, 1)  # 1 month

        payment = Payment(package=self.bronze_1_day)
        duration = payment.get_duration_from_package()
        self.assertEqual(duration, 0)  # 1 day (0 months)

        payment = Payment(package=self.silver_3_months)
        duration = payment.get_duration_from_package()
        self.assertEqual(duration, 3)  # 3 months

    def test_bronze_package_updates_only_active_until(self):
        """Test that BRONZE packages only update active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.bronze_1_month,
            amount=400000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.active_until)
        self.assertIsNone(self.member.pemula_active_until)
        self.assertIsNone(self.member.semi_private_active_until)

    def test_silver_package_updates_active_and_pemula(self):
        """Test that SILVER packages update active_until and pemula_active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.silver_3_months,
            amount=1750000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.active_until)
        self.assertIsNotNone(self.member.pemula_active_until)
        self.assertIsNone(self.member.semi_private_active_until)

    def test_gold_package_updates_active_and_semi_private(self):
        """Test that GOLD packages update active_until and semi_private_active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.gold_6_months,
            amount=4380000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.active_until)
        self.assertIsNone(self.member.pemula_active_until)
        self.assertIsNotNone(self.member.semi_private_active_until)

    def test_platinum_package_updates_all_memberships(self):
        """Test that PLATINUM packages update all membership types"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.platinum_1_month,
            amount=930000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.active_until)
        self.assertIsNotNone(self.member.pemula_active_until)
        self.assertIsNotNone(self.member.semi_private_active_until)

    def test_diamond_package_updates_only_active_until(self):
        """Test that DIAMOND packages only update active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.diamond_2_months,
            amount=3070000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNotNone(self.member.active_until)
        self.assertIsNone(self.member.pemula_active_until)
        self.assertIsNone(self.member.semi_private_active_until)

    def test_add_silver_package_updates_only_pemula(self):
        """Test that ADD-SILVER packages only update pemula_active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.add_silver_1_month,
            amount=300000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNone(self.member.active_until)
        self.assertIsNotNone(self.member.pemula_active_until)
        self.assertIsNone(self.member.semi_private_active_until)

    def test_add_gold_package_updates_only_semi_private(self):
        """Test that ADD-GOLD packages only update semi_private_active_until"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.add_gold_3_months,
            amount=1500000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        self.assertIsNone(self.member.active_until)
        self.assertIsNone(self.member.pemula_active_until)
        self.assertIsNotNone(self.member.semi_private_active_until)

    def test_one_day_package_duration(self):
        """Test that packages with -0 duration create 1-day memberships"""
        payment_date = timezone.now()
        payment = Payment.objects.create(
            member=self.member,
            package=self.bronze_1_day,
            amount=75000,
            payment_date=payment_date,
        )

        self.member.refresh_from_db()
        expected_end_date = payment_date.date()
        self.assertEqual(self.member.active_until.date(), expected_end_date)

    def test_skip_membership_update_field(self):
        """Test that skip_membership_update prevents automatic updates"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.bronze_1_month,
            amount=400000,
            payment_date=timezone.now(),
            skip_membership_update=True,
        )

        self.member.refresh_from_db()
        # Member should not have been updated because skip was True
        self.assertIsNone(self.member.active_until)

    def test_cicilan_enforces_skip_membership_update_model(self):
        """When apakah_nyicil=True, model save enforces skip_membership_update=True."""
        Payment.objects.create(
            member=self.member,
            package=self.bronze_1_month,
            amount=400000,
            payment_date=timezone.now(),
            apakah_nyicil=True,
            skip_membership_update=False,
        )

        payment = Payment.objects.filter(member=self.member).latest("payment_date")
        self.assertTrue(payment.apakah_nyicil)
        self.assertTrue(payment.skip_membership_update)

        self.member.refresh_from_db()
        self.assertIsNone(self.member.active_until)

    def test_membership_stacking_with_packages(self):
        """Test that memberships stack correctly with package-based logic"""
        # Give member an initial active membership
        initial_end_date = timezone.now() + timedelta(days=10)
        self.member.active_until = initial_end_date
        self.member.pemula_active_until = (
            initial_end_date  # Set same date for consistent stacking
        )
        self.member.save()

        # Add a SILVER package
        payment = Payment.objects.create(
            member=self.member,
            package=self.silver_3_months,
            amount=1750000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()

        # Both active_until and pemula_active_until should be extended from the same initial end date
        expected_start_date = initial_end_date.date() + timedelta(days=1)
        expected_end_date = (
            expected_start_date + relativedelta(months=3) - timedelta(days=1)
        )

        self.assertEqual(self.member.active_until.date(), expected_end_date)
        self.assertEqual(self.member.pemula_active_until.date(), expected_end_date)

    def test_skip_membership_update_default_false(self):
        """Test that skip_membership_update defaults to False"""
        payment = Payment.objects.create(
            member=self.member,
            package=self.bronze_1_month,
            amount=400000,
            payment_date=timezone.now(),
        )
        self.assertFalse(payment.skip_membership_update)

    def test_legacy_fallback_when_no_package(self):
        """Test that payments without packages don't auto-update memberships (manual admin update required)"""
        payment = Payment.objects.create(
            member=self.member,
            amount=400000,
            payment_date=timezone.now(),
        )

        self.member.refresh_from_db()
        # Legacy payments should NOT auto-update any memberships - admin handles manually
        self.assertIsNone(self.member.active_until)
        self.assertIsNone(self.member.pemula_active_until)
        self.assertIsNone(self.member.semi_private_active_until)

        # Payment should have membership_end_date set to payment_date for tracking
        self.assertIsNotNone(payment.membership_end_date)
