from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import Member
from .models import Visit


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

    def test_check_in_not_logged_in(self):
        """
        Test that a member who is not logged in can check in successfully.
        """
        response = self.client.post(
            reverse("check_in_page"), {"email": self.active_member.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )
        self.assertEqual(
            self.client.session.get("member_email"), self.active_member.email
        )

    def test_check_in_already_logged_in(self):
        """
        Test that a member who is already logged in is automatically checked in.
        """
        session = self.client.session
        session["member_email"] = self.active_member.email
        session.save()

        response = self.client.get(reverse("check_in_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).exists()
        )

    def test_check_in_with_active_visit(self):
        """
        Test that a member cannot check in if they already have an active visit.
        """
        Visit.objects.create(member=self.active_member)
        response = self.client.post(
            reverse("check_in_page"), {"email": self.active_member.email}
        )
        self.assertEqual(response.status_code, 200)
        # Should only be one active visit
        self.assertEqual(
            Visit.objects.filter(
                member=self.active_member, check_out_time__isnull=True
            ).count(),
            1,
        )

    def test_check_in_inactive_member(self):
        """
        Test that an inactive member cannot check in.
        """
        response = self.client.post(
            reverse("check_in_page"), {"email": self.inactive_member.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Visit.objects.filter(
                member=self.inactive_member, check_out_time__isnull=True
            ).exists()
        )

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
        self.assertIsNone(self.client.session.get("member_email"))
