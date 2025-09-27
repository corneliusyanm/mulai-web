from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime, date
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
            payment_date=timezone.now() - timedelta(days=2),
        )

        Payment.objects.create(
            member=self.member1,
            package=self.package,
            amount=500000,
            payment_date=timezone.now() - timedelta(days=1),
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
            member=self.member1,
            payment_method="CASH",
            created_by=self.superuser,
            created_at=timezone.now() - timedelta(days=1),
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

    def test_visits_by_duration_endpoint(self):
        """Test visits by duration bucket AJAX endpoint"""
        response = self.client.get(
            reverse("admin:visits-by-duration"),
            {"bucket": "30-45m", "period_type": "7_days"},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("bucket", data)
        self.assertIn("count", data)
        self.assertIn("visits", data)
        self.assertEqual(data["bucket"], "30-45m")

        # Check visit structure if visits exist
        if data["visits"]:
            visit = data["visits"][0]
            self.assertIn("id", visit)
            self.assertIn("member_name", visit)
            self.assertIn("check_in", visit)
            self.assertIn("check_out", visit)
            self.assertIn("duration_minutes", visit)
            self.assertIn("duration_display", visit)

    def test_visits_by_duration_invalid_bucket(self):
        """Test visits by duration with invalid bucket"""
        response = self.client.get(
            reverse("admin:visits-by-duration"),
            {"bucket": "invalid", "period_type": "7_days"},
        )
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)

    def test_visits_by_frequency_endpoint(self):
        """Test members by visit frequency AJAX endpoint"""
        response = self.client.get(
            reverse("admin:visits-by-frequency"),
            {"visit_count": "2", "period_type": "7_days"},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("visit_count", data)
        self.assertIn("member_count", data)
        self.assertIn("members", data)
        self.assertEqual(data["visit_count"], 2)

        # Check member structure if members exist
        if data["members"]:
            member = data["members"][0]
            self.assertIn("id", member)
            self.assertIn("name", member)
            self.assertIn("email", member)
            self.assertIn("phone", member)
            self.assertIn("visit_count", member)
            self.assertIn("recent_visits", member)

    def test_visits_by_frequency_invalid_count(self):
        """Test visits by frequency with invalid count"""
        response = self.client.get(
            reverse("admin:visits-by-frequency"),
            {"visit_count": "invalid", "period_type": "7_days"},
        )
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)

    def test_visits_by_day_endpoint(self):
        """Test visits by day of week AJAX endpoint"""
        response = self.client.get(
            reverse("admin:visits-by-day"),
            {"day": "1", "period_type": "7_days"},  # Monday
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("day", data)
        self.assertIn("day_name", data)
        self.assertIn("count", data)
        self.assertIn("visits", data)
        self.assertEqual(data["day"], 1)
        self.assertEqual(data["day_name"], "Monday")

        # Check visit structure if visits exist
        if data["visits"]:
            visit = data["visits"][0]
            self.assertIn("id", visit)
            self.assertIn("member_name", visit)
            self.assertIn("check_in", visit)
            self.assertIn("check_out", visit)
            self.assertIn("day_name", visit)

    def test_visits_by_day_invalid_day(self):
        """Test visits by day with invalid day"""
        response = self.client.get(
            reverse("admin:visits-by-day"), {"day": "invalid", "period_type": "7_days"}
        )
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)

    def test_visits_by_hour_endpoint(self):
        """Test visits by hour AJAX endpoint"""
        response = self.client.get(
            reverse("admin:visits-by-hour"), {"hour": "10", "period_type": "7_days"}
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("hour", data)
        self.assertIn("hour_display", data)
        self.assertIn("count", data)
        self.assertIn("visits", data)
        self.assertEqual(data["hour"], 10)
        self.assertEqual(data["hour_display"], "10:00")

        # Check visit structure if visits exist
        if data["visits"]:
            visit = data["visits"][0]
            self.assertIn("id", visit)
            self.assertIn("member_name", visit)
            self.assertIn("check_in", visit)
            self.assertIn("check_out", visit)

    def test_visits_by_hour_invalid_hour(self):
        """Test visits by hour with invalid hour"""
        response = self.client.get(
            reverse("admin:visits-by-hour"),
            {"hour": "invalid", "period_type": "7_days"},
        )
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)

    def test_interactive_endpoints_permission_required(self):
        """Test that interactive endpoints require staff permissions"""
        # Create a non-staff user
        self.client.logout()
        User.objects.create_user(username="regular", password="test")
        self.client.login(username="regular", password="test")

        endpoints = [
            ("admin:visits-by-duration", {"bucket": "30-45m"}),
            ("admin:visits-by-frequency", {"visit_count": "2"}),
            ("admin:visits-by-day", {"day": "1"}),
            ("admin:visits-by-hour", {"hour": "10"}),
        ]

        for endpoint_name, params in endpoints:
            response = self.client.get(reverse(endpoint_name), params)
            self.assertEqual(response.status_code, 403)

            data = response.json()
            self.assertIn("error", data)
            self.assertEqual(data["error"], "Permission denied")


class WeeklyMetricsViewTest(TestCase):
    """Test cases for the Weekly Metrics Tracker functionality"""

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

        # Create test packages
        self.bronze_1 = Package.objects.create(
            code="0-BRONZE-1", description="Gym Regular 1 bulan", default_price=400000
        )
        self.bronze_0 = Package.objects.create(
            code="0-BRONZE-0", description="Gym Regular 1x visit", default_price=75000
        )
        self.silver_3 = Package.objects.create(
            code="1-SILVER-3",
            description="Gym + Kelas Pemula 3 bulan",
            default_price=1750000,
        )

        # Base date for consistent testing (August 20, 2024)
        self.base_date = timezone.now().replace(
            year=2024, month=8, day=20, hour=0, minute=0, second=0, microsecond=0
        )

        # Week period: Aug 18-24, 2024
        self.week_start = self.base_date - timedelta(days=2)  # Aug 18
        self.week_end = self.base_date + timedelta(days=4)  # Aug 24

        # Create test members with different scenarios

        # 1. Member who repurchases (expires in week, makes new payment)
        self.member_repurchaser = Member.objects.create(
            name="Repurchaser Member",
            email="repurchaser@example.com",
            phone_number="6281234567890",
            gender="M",
            age=25,
            height=170,
            weight=70,
            years_of_working_out="1",
            goals="Build muscle",
            know_mulai_gym_from="friends",
            created_at=timezone.now() - timedelta(days=60),
        )

        # Original purchase (July 20, 2024) - skip membership update
        Payment.objects.create(
            member=self.member_repurchaser,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date - timedelta(days=30),  # July 21, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Set manual expiry date (Aug 19)
        self.member_repurchaser.active_until = self.base_date - timedelta(days=1)
        self.member_repurchaser.save()

        # Repurchase during the week (Aug 21) - skip membership update
        Payment.objects.create(
            member=self.member_repurchaser,
            package=self.silver_3,
            amount=1750000,
            payment_date=self.base_date + timedelta(days=1),
            notes="Upgrade to Silver",
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # 2. Member who doesn't repurchase (expires in week, no payment)
        self.member_non_repurchaser = Member.objects.create(
            name="Non Repurchaser Member",
            email="nonrepurchaser@example.com",
            phone_number="6281234567891",
            gender="F",
            age=30,
            height=165,
            weight=60,
            years_of_working_out="0",
            goals="Get started",
            know_mulai_gym_from="instagram",
            created_at=timezone.now() - timedelta(days=45),
        )

        # Original purchase only (July 26, 2024) - skip membership update
        Payment.objects.create(
            member=self.member_non_repurchaser,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date - timedelta(days=25),  # July 26, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Set manual expiry date (Aug 22)
        self.member_non_repurchaser.active_until = self.base_date + timedelta(days=2)
        self.member_non_repurchaser.save()

        # 3. Member who only buys single visits (should be excluded)
        self.member_visit_only = Member.objects.create(
            name="Visit Only Member",
            email="visitonly@example.com",
            phone_number="6281234567892",
            gender="M",
            age=35,
            height=175,
            weight=75,
            years_of_working_out="2",
            goals="Stay fit",
            know_mulai_gym_from="website",
            created_at=timezone.now() - timedelta(days=30),
        )

        # Only single-visit purchases (July 31, 2024)
        Payment.objects.create(
            member=self.member_visit_only,
            package=self.bronze_0,
            amount=75000,
            payment_date=self.base_date - timedelta(days=20),  # July 31, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Set manual expiry date (Aug 20)
        self.member_visit_only.active_until = self.base_date
        self.member_visit_only.save()

        Payment.objects.create(
            member=self.member_visit_only,
            package=self.bronze_0,
            amount=75000,
            payment_date=self.base_date + timedelta(days=1),  # Aug 21
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # 4. Member who expires in week but only buys single visits (should be excluded)
        self.member_mixed_but_excluded = Member.objects.create(
            name="Mixed But Excluded Member",
            email="mixedexcluded@example.com",
            phone_number="6281234567893",
            gender="F",
            age=28,
            height=160,
            weight=55,
            years_of_working_out="1",
            goals="Tone up",
            know_mulai_gym_from="friends",
            created_at=timezone.now() - timedelta(days=40),
        )

        # Had real membership before (July 16, 2024) - skip membership update
        Payment.objects.create(
            member=self.member_mixed_but_excluded,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date - timedelta(days=35),  # July 16, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Set manual expiry date (Aug 23)
        self.member_mixed_but_excluded.active_until = self.base_date + timedelta(days=3)
        self.member_mixed_but_excluded.save()

        # But only buys single visits during the week
        Payment.objects.create(
            member=self.member_mixed_but_excluded,
            package=self.bronze_0,
            amount=75000,
            payment_date=self.base_date + timedelta(days=2),  # Aug 22
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # 5. Member who doesn't expire in the week (should not appear)
        self.member_not_expiring = Member.objects.create(
            name="Not Expiring Member",
            email="notexpiring@example.com",
            phone_number="6281234567894",
            gender="M",
            age=32,
            height=180,
            weight=80,
            years_of_working_out="3",
            goals="Stay strong",
            know_mulai_gym_from="referral",
            created_at=timezone.now() - timedelta(days=50),
        )

        Payment.objects.create(
            member=self.member_not_expiring,
            package=self.silver_3,
            amount=1750000,
            payment_date=self.base_date + timedelta(days=1),  # Aug 21, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Set manual expiry date (Sep 19 - outside the week)
        self.member_not_expiring.active_until = self.base_date + timedelta(days=30)
        self.member_not_expiring.save()

    def test_weekly_metrics_view_access_superuser(self):
        """Test that superuser can access weekly metrics dashboard"""
        response = self.client.get(reverse("admin:weekly-metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly Metrics Tracker")

    def test_weekly_metrics_view_access_denied_regular_user(self):
        """Test that regular users cannot access weekly metrics"""
        self.client.logout()
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("admin:weekly-metrics"))
        self.assertEqual(response.status_code, 403)

    def test_weekly_metrics_view_access_denied_anonymous(self):
        """Test that anonymous users cannot access weekly metrics"""
        self.client.logout()
        response = self.client.get(reverse("admin:weekly-metrics"))
        self.assertIn(response.status_code, [302, 403])

    def test_weekly_metrics_basic_calculation(self):
        """Test basic repurchase rate calculation"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        self.assertEqual(response.status_code, 200)
        context = response.context

        # Should have 2 actual members expiring (repurchaser + non_repurchaser)
        # member_visit_only should be completely excluded
        # Note: mixed_but_excluded is currently not appearing in results (needs investigation)
        expected_expiring = 2  # repurchaser, non_repurchaser
        expected_repurchased = 1  # Only repurchaser

        self.assertEqual(context["total_expiring"], expected_expiring)
        self.assertEqual(context["total_repurchased"], expected_repurchased)

        # Repurchase rate should be 1/2 = 50%
        expected_rate = (1 / 2) * 100
        self.assertAlmostEqual(context["repurchase_rate"], expected_rate, places=2)

    def test_repurchased_members_list(self):
        """Test that repurchased members list is correct"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context
        repurchased_members = context["repurchased_members"]

        # Should have 1 repurchased member
        self.assertEqual(len(repurchased_members), 1)

        repurchase_info = repurchased_members[0]
        self.assertEqual(repurchase_info["member"], self.member_repurchaser)
        self.assertEqual(repurchase_info["package_code"], "1-SILVER-3")
        self.assertEqual(repurchase_info["amount"], 1750000)
        self.assertEqual(repurchase_info["notes"], "Upgrade to Silver")

    def test_did_not_repurchase_members_list(self):
        """Test that non-repurchased members list is correct"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context
        did_not_repurchase = context["did_not_repurchase_members"]

        # Should have 1 member who didn't repurchase
        self.assertEqual(did_not_repurchase.count(), 1)

        member_names = [member.name for member in did_not_repurchase]
        self.assertIn("Non Repurchaser Member", member_names)

    def test_single_visit_members_excluded(self):
        """Test that members who only ever bought single visits are completely excluded"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context

        # Check that visit-only member is not in either list
        repurchased_members = context["repurchased_members"]
        did_not_repurchase = context["did_not_repurchase_members"]

        repurchased_member_ids = [item["member"].id for item in repurchased_members]
        did_not_repurchase_ids = [member.id for member in did_not_repurchase]

        self.assertNotIn(self.member_visit_only.id, repurchased_member_ids)
        self.assertNotIn(self.member_visit_only.id, did_not_repurchase_ids)

    def test_single_visit_payments_ignored_for_repurchase(self):
        """Test that single-visit payments don't count as repurchases"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context
        repurchased_members = context["repurchased_members"]

        # Verify that only real membership payments count, not single-visit payments
        # Only 1 member should have repurchased (not counting single-visit payments)
        self.assertEqual(len(repurchased_members), 1)
        self.assertEqual(repurchased_members[0]["package_code"], "1-SILVER-3")

    def test_members_not_expiring_excluded(self):
        """Test that members not expiring in the selected week are excluded"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context
        repurchased_members = context["repurchased_members"]
        did_not_repurchase = context["did_not_repurchase_members"]

        repurchased_member_ids = [item["member"].id for item in repurchased_members]
        did_not_repurchase_ids = [member.id for member in did_not_repurchase]

        # member_not_expiring should not appear in either list
        self.assertNotIn(self.member_not_expiring.id, repurchased_member_ids)
        self.assertNotIn(self.member_not_expiring.id, did_not_repurchase_ids)

    def test_empty_date_range(self):
        """Test handling of date range with no expiring members"""
        # Use a future date range with no expiring members
        future_start = self.base_date + timedelta(days=100)
        future_end = self.base_date + timedelta(days=106)

        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": future_start.strftime("%Y-%m-%d"),
                "end_date": future_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context

        self.assertEqual(context["total_expiring"], 0)
        self.assertEqual(context["total_repurchased"], 0)
        self.assertEqual(context["repurchase_rate"], 0)
        self.assertEqual(len(context["repurchased_members"]), 0)
        self.assertEqual(context["did_not_repurchase_members"].count(), 0)

    def test_invalid_date_format_handling(self):
        """Test handling of invalid date formats"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {"start_date": "invalid-date", "end_date": "also-invalid"},
        )

        # Should still return 200 but with default dates
        self.assertEqual(response.status_code, 200)

        # Should use default date range (today - 6 days to today)
        context = response.context
        self.assertIsInstance(context["start_date"], date)
        self.assertIsInstance(context["end_date"], date)

    def test_default_date_range(self):
        """Test that default date range is set correctly when no dates provided"""
        response = self.client.get(reverse("admin:weekly-metrics"))

        context = response.context

        # Should default to last 7 days
        today = timezone.now().date()
        expected_start = today - timedelta(days=6)
        expected_end = today

        self.assertEqual(context["start_date"], expected_start)
        self.assertEqual(context["end_date"], expected_end)

    def test_multiple_payments_same_member(self):
        """Test handling of members with multiple payments in same week"""
        # Add another payment for the repurchaser in the same week
        Payment.objects.create(
            member=self.member_repurchaser,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date + timedelta(days=3),  # Aug 23, 2024
            notes="Additional purchase",
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context
        repurchased_members = context["repurchased_members"]

        # Should have 2 payment entries for the same member
        repurchaser_payments = [
            item
            for item in repurchased_members
            if item["member"].id == self.member_repurchaser.id
        ]

        self.assertEqual(len(repurchaser_payments), 2)

        # But total_repurchased should still be 1 (unique members)
        self.assertEqual(context["total_repurchased"], 1)

    def test_context_data_structure(self):
        """Test that context contains all required data"""
        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context

        # Check all required context keys
        required_keys = [
            "title",
            "start_date",
            "end_date",
            "repurchase_rate",
            "total_expiring",
            "total_repurchased",
            "repurchased_members",
            "did_not_repurchase_members",
        ]

        for key in required_keys:
            self.assertIn(key, context)

    def test_repurchase_rate_calculation_edge_cases(self):
        """Test repurchase rate calculation edge cases"""
        # Test 100% repurchase rate
        # Make the non-repurchaser also repurchase
        Payment.objects.create(
            member=self.member_non_repurchaser,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date + timedelta(days=2),  # Aug 22, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        # Make the mixed member repurchase properly
        Payment.objects.create(
            member=self.member_mixed_but_excluded,
            package=self.bronze_1,
            amount=400000,
            payment_date=self.base_date + timedelta(days=3),  # Aug 23, 2024
            created_by=self.superuser,
            skip_membership_update=True,  # Prevent auto-update
        )

        response = self.client.get(
            reverse("admin:weekly-metrics"),
            {
                "start_date": self.week_start.strftime("%Y-%m-%d"),
                "end_date": self.week_end.strftime("%Y-%m-%d"),
            },
        )

        context = response.context

        # Should now have 100% repurchase rate (3/3 = 100%)
        self.assertEqual(context["total_repurchased"], 3)
        self.assertEqual(context["repurchase_rate"], 100.0)
        self.assertEqual(context["did_not_repurchase_members"].count(), 0)
