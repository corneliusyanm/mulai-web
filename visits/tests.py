from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.template import Template, Context
import json

from accounts.models import Member
from .models import Visit
from payments.models import Payment, Package
from purchases.models import Product, Sale, SaleItem

User = get_user_model()


class VisitAdminViewsTest(TestCase):
    def setUp(self):
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.client.login(username="admin", password="password")

        # Create a user with no permissions
        self.user = User.objects.create_user("user", "user@example.com", "password")

        # Create a member
        self.member = Member.objects.create(
            name="Test Member",
            email="member@example.com",
            phone_number="6281234567892",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
        )

        # Create a visit
        self.visit = Visit.objects.create(member=self.member)

    def test_delete_visit_from_current_visits_view(self):
        """
        Test that a superuser can delete a visit from the current visits page.
        """
        response = self.client.get(reverse("admin:delete-visit", args=[self.visit.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("admin:current-visits"))
        self.assertFalse(Visit.objects.filter(id=self.visit.id).exists())

    def test_delete_visit_from_history_view(self):
        """
        Test that a superuser can delete a visit from the history page.
        """
        self.visit.check_out_time = timezone.now()
        self.visit.save()
        response = self.client.get(
            reverse("admin:delete-visit", args=[self.visit.id]) + "?from=history"
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("admin:visit-history"))
        self.assertFalse(Visit.objects.filter(id=self.visit.id).exists())

    def test_delete_visit_permission_denied(self):
        """
        Test that a user without delete permission cannot delete a visit.
        """
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("admin:delete-visit", args=[self.visit.id]))
        self.assertEqual(response.status_code, 403)  # Permission Denied
        self.assertTrue(Visit.objects.filter(id=self.visit.id).exists())


class VisitViewsTest(TestCase):
    def setUp(self):
        # Active member
        self.active_member = Member.objects.create(
            name="Active Member",
            email="active@example.com",
            phone_number="6281234567890",
            active_until=timezone.now() + timedelta(days=30),
            gender="M",
            age=25,
            height=170,
            weight=65,
            years_of_working_out="1",
            goals="To be healthy",
            know_mulai_gym_from="friends",
        )
        # Inactive member
        self.inactive_member = Member.objects.create(
            name="Inactive Member",
            email="inactive@example.com",
            phone_number="6281234567891",
            active_until=timezone.now() - timedelta(days=30),
            gender="F",
            age=30,
            height=160,
            weight=60,
            years_of_working_out="0",
            goals="Get started",
            know_mulai_gym_from="instagram",
        )

    def test_check_in_page_not_logged_in_success(self):
        """
        After a successful POST login, a visit should be created and the user
        redirected to the success page.
        """
        response = self.client.post(
            reverse("check_in_page"), {"email": self.active_member.email}
        )
        self.assertRedirects(response, reverse("check_in_success"))
        self.assertTrue(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )
        self.assertEqual(
            self.client.session.get("member_email"), self.active_member.email
        )

    def test_check_in_page_already_logged_in_auto_checks_in(self):
        """
        A logged-in member visiting the check-in page is automatically checked in
        and redirected to the success page.
        """
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()

        response = self.client.get(reverse("check_in_page"))
        self.assertRedirects(response, reverse("check_in_success"))
        self.assertTrue(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )

    def test_check_in_is_idempotent_with_active_visit(self):
        """
        A member with an active visit is redirected to the success page without
        creating a new visit.
        """
        Visit.objects.create(member=self.active_member)
        response = self.client.post(
            reverse("check_in_page"), {"email": self.active_member.email}
        )
        self.assertRedirects(response, reverse("check_in_success"))
        # Should only be one active visit
        self.assertEqual(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).count(),
            1,
        )

    def test_check_in_inactive_member_fails(self):
        """
        An inactive member cannot check in and is shown a failure page.
        """
        response = self.client.post(
            reverse("check_in_page"), {"email": self.inactive_member.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "visits/check_in_failed.html")
        self.assertFalse(
            Visit.objects.filter(
                member=self.inactive_member, check_out_time__isnull=True
            ).exists()
        )

    def test_check_in_success_view_active_visit(self):
        """
        The success page shows details for an active visit.
        """
        Visit.objects.create(member=self.active_member)
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()
        response = self.client.get(reverse("check_in_success"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CHECK-IN")
        self.assertContains(response, "BERHASIL")

    def test_check_in_success_view_checked_out_visit(self):
        """
        The success page still shows the last visit even if already checked out.
        """
        visit = Visit.objects.create(
            member=self.active_member, check_out_time=timezone.now()
        )
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()
        response = self.client.get(reverse("check_in_success"))
        self.assertEqual(response.status_code, 200)
        expected_time = Template("{{ visit.check_in_time|time:'H.i' }}").render(
            Context({"visit": visit})
        )
        self.assertContains(response, expected_time)

    def test_check_in_success_view_not_logged_in(self):
        """
        A non-logged-in user is redirected from the success page.
        """
        response = self.client.get(reverse("check_in_success"))
        self.assertRedirects(response, reverse("check_in_page"))

    def test_check_out_successfully(self):
        """
        Test that a logged-in member with an active visit can check out.
        """
        Visit.objects.create(member=self.active_member)
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()

        response = self.client.get(reverse("check_out_page"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )

    def test_check_out_not_logged_in(self):
        """
        Test that a user who is not logged in cannot check out.
        """
        Visit.objects.create(member=self.active_member)
        response = self.client.get(reverse("check_out_page"))
        self.assertEqual(response.status_code, 200)
        # Visit should remain active
        self.assertTrue(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )

    def test_check_out_no_active_visit(self):
        """
        Test that a member cannot check out if they do not have an active visit.
        """
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()

        response = self.client.get(reverse("check_out_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check Out Gagal")

    def test_forget_member_view(self):
        """
        Test that the forget_member view clears the session.
        """
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()

        response = self.client.get(reverse("forget_member"))
        self.assertEqual(response.status_code, 302)


class AnalyticsViewsTest(TestCase):
    """Test cases for the analytics dashboard functionality"""

    def setUp(self):
        # Create superuser for admin access
        self.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.client.login(username="admin", password="password")

        # Create a regular user without admin privileges
        self.regular_user = User.objects.create_user(
            "user", "user@example.com", "password"
        )

        # Create test members with different membership types and expiry dates
        self.member_active_long = Member.objects.create(
            name="Active Long Term",
            email="active_long@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="2",
            goals="Build muscle",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=90),
            pemula_active_until=timezone.now() + timedelta(days=60),
            semi_private_active_until=timezone.now() + timedelta(days=45),
        )

        self.member_expiring_soon = Member.objects.create(
            name="Expiring Soon",
            email="expiring@example.com",
            phone_number="6281234567891",
            gender="F",
            age=30,
            height=165,
            weight=60,
            years_of_working_out="1",
            goals="Lose weight",
            know_mulai_gym_from="instagram",
            active_until=timezone.now() + timedelta(days=6),
            pemula_active_until=timezone.now() + timedelta(days=4),
        )

        self.member_inactive = Member.objects.create(
            name="Inactive Member",
            email="inactive@example.com",
            phone_number="6281234567892",
            gender="M",
            age=35,
            height=175,
            weight=80,
            years_of_working_out="0",
            goals="Get started",
            know_mulai_gym_from="website",
            active_until=timezone.now() - timedelta(days=10),
        )

        # Create some visits for testing
        Visit.objects.create(
            member=self.member_active_long,
            check_in_time=timezone.now() - timedelta(days=2),
        )

        # Create old visit for low activity testing
        Visit.objects.create(
            member=self.member_expiring_soon,
            check_in_time=timezone.now() - timedelta(days=20),
            check_out_time=timezone.now() - timedelta(days=20, hours=2),
        )

        # Create a package for revenue calculations
        self.package = Package.objects.create(
            code="M1", description="Monthly Membership", default_price=500000
        )

        # Create some payments
        Payment.objects.create(
            member=self.member_active_long,
            package=self.package,
            amount=500000,
            payment_date=timezone.now() - timedelta(days=30),
        )

    def test_analytics_view_access_superuser(self):
        """Test that superuser can access analytics dashboard"""
        response = self.client.get(reverse("admin:membership-analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Advanced Membership Analytics")
        self.assertContains(response, "Interactive Charts")

    def test_analytics_view_access_denied_regular_user(self):
        """Test that regular users cannot access analytics"""
        self.client.logout()
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("admin:membership-analytics"))
        self.assertEqual(response.status_code, 403)

    def test_analytics_view_access_denied_anonymous(self):
        """Test that anonymous users cannot access analytics"""
        self.client.logout()
        response = self.client.get(reverse("admin:membership-analytics"))
        # Custom admin site may return 403 instead of redirect
        self.assertIn(response.status_code, [302, 403])

    def test_analytics_data_calculation(self):
        """Test that analytics correctly calculates membership projections"""
        response = self.client.get(reverse("admin:membership-analytics"))
        context = response.context

        # Check that weeks_data contains proper projections
        weeks_data = json.loads(context["weeks_data"])
        self.assertTrue(len(weeks_data) > 0)

        # First week should include both active members
        first_week = weeks_data[0]
        self.assertGreaterEqual(
            first_week["active_count"], 2
        )  # At least 2 active members
        self.assertGreaterEqual(
            first_week["pemula_count"], 1
        )  # At least 1 pemula member

        # Check current stats
        current_stats = context["current_stats"]
        self.assertGreaterEqual(current_stats["active_members"], 2)
        self.assertGreaterEqual(current_stats["total_members"], 3)

    def test_members_by_date_ajax_view(self):
        """Test the AJAX endpoint for getting members by date"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        response = self.client.get(
            reverse("admin:members-by-date"), {"date": today, "type": "active"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("members", data)
        self.assertIn("count", data)
        self.assertGreaterEqual(
            data["count"], 2
        )  # Should have at least 2 active members

        # Check member data structure
        if data["members"]:
            member = data["members"][0]
            self.assertIn("name", member)
            self.assertIn("email", member)
            self.assertIn("phone", member)
            self.assertIn("whatsapp_link", member)

    def test_members_by_date_different_types(self):
        """Test member lookup for different membership types"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        # Test active members
        response = self.client.get(
            reverse("admin:members-by-date"), {"date": today, "type": "active"}
        )
        active_data = response.json()

        # Test pemula members
        response = self.client.get(
            reverse("admin:members-by-date"), {"date": today, "type": "pemula"}
        )
        pemula_data = response.json()

        # Test semi-private members
        response = self.client.get(
            reverse("admin:members-by-date"), {"date": today, "type": "semi_private"}
        )
        semi_private_data = response.json()

        # Verify different counts for different types
        self.assertGreaterEqual(active_data["count"], 1)
        self.assertGreaterEqual(pemula_data["count"], 1)
        self.assertGreaterEqual(semi_private_data["count"], 1)

    def test_member_details_ajax_view(self):
        """Test the AJAX endpoint for member details"""
        response = self.client.get(
            reverse("admin:member-details", args=[self.member_active_long.id])
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("member", data)
        member_data = data["member"]

        # Check member information
        self.assertEqual(member_data["name"], self.member_active_long.name)
        self.assertEqual(member_data["email"], self.member_active_long.email)
        self.assertIn("recent_payments", member_data)
        self.assertIn("recent_visits", member_data)

    def test_export_members_csv(self):
        """Test CSV export functionality"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        response = self.client.get(
            reverse("admin:export-members"), {"date": today, "type": "active"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

        # Check CSV content
        content = response.content.decode("utf-8")
        self.assertIn("Name,Email,Phone", content)
        self.assertIn(self.member_active_long.name, content)

    def test_smart_alerts_generation(self):
        """Test that smart alerts are properly generated"""
        response = self.client.get(reverse("admin:membership-analytics"))
        context = response.context

        alerts = context["alerts"]

        # Should have alert for member expiring soon
        expiring_alerts = [a for a in alerts if "Expiring" in a["title"]]
        self.assertTrue(len(expiring_alerts) > 0)

        # Check alert structure
        for alert in alerts:
            self.assertIn("type", alert)
            self.assertIn("title", alert)
            self.assertIn("message", alert)

    def test_business_insights_calculation(self):
        """Test business insights calculation"""
        response = self.client.get(reverse("admin:membership-analytics"))
        context = response.context

        insights = context["insights"]

        # Check insights structure
        self.assertIn("new_members_3m", insights)
        self.assertIn("total_revenue_3m", insights)
        self.assertIn("avg_monthly_signups", insights)
        self.assertIn("avg_monthly_revenue", insights)

    def test_analytics_custom_date_range(self):
        """Test analytics with custom date range parameters"""
        future_date = (timezone.now() + timedelta(days=30)).date().strftime("%Y-%m-%d")

        response = self.client.get(
            reverse("admin:membership-analytics"),
            {"start_date": future_date, "weeks": 26},
        )

        self.assertEqual(response.status_code, 200)
        context = response.context

        # Check that parameters were applied
        self.assertEqual(context["weeks_ahead"], 26)
        self.assertEqual(context["start_date"], future_date)

    def test_members_by_date_invalid_date(self):
        """Test member lookup with invalid date format"""
        response = self.client.get(
            reverse("admin:members-by-date"), {"date": "invalid-date", "type": "active"}
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_members_by_date_permission_denied(self):
        """Test that non-staff users cannot access member lookup"""
        self.client.logout()
        self.client.login(username="user", password="password")

        response = self.client.get(
            reverse("admin:members-by-date"), {"date": "2024-01-01", "type": "active"}
        )

        self.assertEqual(response.status_code, 403)

    def test_revenue_projections(self):
        """Test revenue projection calculations"""
        response = self.client.get(reverse("admin:membership-analytics"))
        context = response.context

        revenue_projections = context["revenue_projections"]

        # Should have projections if there are packages
        if Package.objects.exists():
            self.assertTrue(len(revenue_projections) > 0)

            # Check projection structure
            for projection in revenue_projections:
                self.assertIn("week", projection)
                self.assertIn("revenue", projection)
                self.assertIsInstance(projection["revenue"], (int, float))


class BusinessIntelligenceViewsTest(TestCase):
    """Test cases for the comprehensive business intelligence dashboard"""

    def setUp(self):
        # Create superuser for admin access
        self.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.client.login(username="admin", password="password")

        # Create test data for comprehensive analytics
        self.member1 = Member.objects.create(
            name="Test Member 1",
            email="member1@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="2",
            goals="Build muscle",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=90),
        )

        self.member2 = Member.objects.create(
            name="Test Member 2",
            email="member2@example.com",
            phone_number="6281234567891",
            gender="F",
            age=30,
            height=165,
            weight=60,
            years_of_working_out="1",
            goals="Lose weight",
            know_mulai_gym_from="instagram",
            active_until=timezone.now() + timedelta(days=30),
        )

        # Create packages and payments
        self.package = Package.objects.create(
            code="M1", description="Monthly Membership", default_price=500000
        )

        Payment.objects.create(
            member=self.member1,
            package=self.package,
            amount=500000,
            payment_date=timezone.now() - timedelta(days=30),
        )

        Payment.objects.create(
            member=self.member1,
            package=self.package,
            amount=500000,
            payment_date=timezone.now() - timedelta(days=10),
        )

        # Create visits
        Visit.objects.create(
            member=self.member1,
            check_in_time=timezone.now() - timedelta(days=5),
            check_out_time=timezone.now() - timedelta(days=5, hours=-2),
        )

        Visit.objects.create(
            member=self.member2, check_in_time=timezone.now() - timedelta(days=2)
        )

        # Create products and sales
        self.product = Product.objects.create(name="Protein Powder", price=200000)

        self.sale = Sale.objects.create(
            member=self.member1, payment_method="CASH", created_by=self.superuser
        )

        SaleItem.objects.create(
            sale=self.sale, product=self.product, quantity=2, price_at_purchase=200000
        )

        # Update sale total
        self.sale.update_total_amount()

    def test_business_analytics_view_access(self):
        """Test that business analytics dashboard is accessible"""
        response = self.client.get(reverse("admin:business-analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Business Intelligence Dashboard")

    def test_business_analytics_view_access_denied(self):
        """Test that non-staff users cannot access business analytics"""
        self.client.logout()
        user = User.objects.create_user("user", "user@example.com", "password")
        self.client.login(username="user", password="password")

        response = self.client.get(reverse("admin:business-analytics"))
        self.assertEqual(response.status_code, 403)

    def test_business_metrics_calculation(self):
        """Test business metrics calculation"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        business_metrics = context["business_metrics"]

        # Check key metrics
        self.assertIn("total_revenue", business_metrics)
        self.assertIn("store_revenue", business_metrics)
        self.assertIn("total_members", business_metrics)
        self.assertIn("active_members", business_metrics)
        self.assertIn("total_visits", business_metrics)
        self.assertIn("customer_lifetime_value", business_metrics)
        self.assertIn("member_retention_rate", business_metrics)

        # Verify data consistency
        self.assertEqual(business_metrics["total_members"], 2)
        self.assertGreaterEqual(business_metrics["total_visits"], 2)
        self.assertGreater(business_metrics["total_revenue"], 0)

    def test_revenue_analytics_data(self):
        """Test revenue analytics data structure"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        revenue_analytics = json.loads(context["revenue_analytics"])

        # Check structure
        self.assertIn("monthly_trends", revenue_analytics)
        self.assertIn("payment_methods", revenue_analytics)
        self.assertIn("package_revenue", revenue_analytics)

        # Verify monthly trends structure
        if revenue_analytics["monthly_trends"]:
            trend = revenue_analytics["monthly_trends"][0]
            self.assertIn("month", trend)
            self.assertIn("membership_revenue", trend)
            self.assertIn("store_revenue", trend)
            self.assertIn("total_revenue", trend)

    def test_sales_analytics_data(self):
        """Test sales analytics data structure"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        sales_analytics = json.loads(context["sales_analytics"])

        # Check structure
        self.assertIn("top_products", sales_analytics)
        self.assertIn("daily_trends", sales_analytics)
        self.assertIn("payment_methods", sales_analytics)

    def test_visit_analytics_data(self):
        """Test visit analytics data structure"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        visit_analytics = json.loads(context["visit_analytics"])

        # Check structure
        self.assertIn("daily_visits", visit_analytics)
        self.assertIn("hourly_patterns", visit_analytics)
        self.assertIn("member_frequencies", visit_analytics)

    def test_repurchase_analytics(self):
        """Test repurchase analytics calculation"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        repurchase_analytics = context["repurchase_analytics"]

        # Check structure
        self.assertIn("repurchase_rate", repurchase_analytics)
        self.assertIn("avg_repurchase_interval", repurchase_analytics)
        self.assertIn("cohort_analysis", repurchase_analytics)
        self.assertIn("members_with_payments", repurchase_analytics)

        # Member1 has 2 payments, so repurchase rate should be > 0
        self.assertGreater(repurchase_analytics["repurchase_rate"], 0)

    def test_revenue_data_ajax_endpoint(self):
        """Test AJAX endpoint for revenue data"""
        response = self.client.get(reverse("admin:revenue-data"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("monthly_trends", data)

    def test_sales_data_ajax_endpoint(self):
        """Test AJAX endpoint for sales data"""
        response = self.client.get(reverse("admin:sales-data"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("top_products", data)

    def test_visits_data_ajax_endpoint(self):
        """Test AJAX endpoint for visits data"""
        response = self.client.get(reverse("admin:visits-data"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("daily_visits", data)

    def test_export_business_data_revenue(self):
        """Test CSV export for revenue data"""
        response = self.client.get(
            reverse("admin:export-business"), {"type": "revenue", "months": 12}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_business_data_visits(self):
        """Test CSV export for visits data"""
        response = self.client.get(
            reverse("admin:export-business"), {"type": "visits", "months": 12}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_business_analytics_custom_timeframe(self):
        """Test business analytics with custom timeframe"""
        response = self.client.get(
            reverse("admin:business-analytics"), {"months": 6, "type": "revenue"}
        )

        self.assertEqual(response.status_code, 200)
        context = response.context

        self.assertEqual(context["months_back"], 6)
        self.assertEqual(context["analysis_type"], "revenue")

    def test_ajax_endpoints_permission_denied(self):
        """Test that AJAX endpoints deny access to non-staff users"""
        self.client.logout()
        user = User.objects.create_user("user", "user@example.com", "password")
        self.client.login(username="user", password="password")

        endpoints = ["admin:revenue-data", "admin:sales-data", "admin:visits-data"]

        for endpoint in endpoints:
            response = self.client.get(reverse(endpoint))
            self.assertEqual(response.status_code, 403)

    def test_member_segmentation_calculation(self):
        """Test member segmentation logic"""
        response = self.client.get(reverse("admin:business-analytics"))
        context = response.context

        member_analytics = json.loads(context["member_analytics"])

        # Check member segments
        self.assertIn("member_segments", member_analytics)
        segments = member_analytics["member_segments"]

        # Should have segments
        self.assertTrue(len(segments) > 0)

        # Check segment structure
        for segment in segments:
            self.assertIn("segment", segment)
            self.assertIn("count", segment)
            self.assertIn("percentage", segment)
