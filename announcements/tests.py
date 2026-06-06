import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Announcement


def _make(message="Halo", level=Announcement.Level.INFO, active=True,
          start_offset_hours=-1, end_offset_hours=1, priority=0):
    """Create an Announcement with a window relative to now."""
    now = timezone.now()
    return Announcement.objects.create(
        message=message,
        level=level,
        is_active=active,
        starts_at=now + timedelta(hours=start_offset_hours),
        ends_at=now + timedelta(hours=end_offset_hours),
        priority=priority,
    )


class AnnouncementModelTests(TestCase):
    def test_str(self):
        a = _make(message="Besok libur", level=Announcement.Level.URGENT)
        self.assertIn("Darurat", str(a))
        self.assertIn("Besok libur", str(a))

    def test_is_live_within_window_and_active(self):
        self.assertTrue(_make().is_live)

    def test_not_live_when_inactive(self):
        self.assertFalse(_make(active=False).is_live)

    def test_not_live_before_window(self):
        self.assertFalse(_make(start_offset_hours=1, end_offset_hours=2).is_live)

    def test_not_live_after_window(self):
        self.assertFalse(_make(start_offset_hours=-2, end_offset_hours=-1).is_live)

    def test_clean_rejects_end_before_start(self):
        now = timezone.now()
        a = Announcement(
            message="x",
            starts_at=now,
            ends_at=now - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            a.clean()

    def test_get_live_excludes_inactive_and_out_of_window(self):
        live = _make(message="live")
        _make(message="inactive", active=False)
        _make(message="future", start_offset_hours=1, end_offset_hours=2)
        _make(message="past", start_offset_hours=-2, end_offset_hours=-1)
        result = list(Announcement.get_live())
        self.assertEqual(result, [live])

    def test_get_live_ordered_by_priority_desc(self):
        low = _make(message="low", priority=1)
        high = _make(message="high", priority=10)
        result = list(Announcement.get_live())
        self.assertEqual(result, [high, low])

    def test_clean_accepts_valid_window(self):
        now = timezone.now()
        a = Announcement(message="x", starts_at=now, ends_at=now + timedelta(hours=1))
        a.clean()  # must not raise


class ActiveAnnouncementsViewTests(TestCase):
    def setUp(self):
        self.url = reverse("announcements:active")

    def test_returns_only_live_announcements(self):
        live = _make(message="Tayang", priority=5)
        _make(message="Mati", active=False)
        _make(message="Nanti", start_offset_hours=2, end_offset_hours=3)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        messages = [a["message"] for a in data["announcements"]]
        self.assertEqual(messages, ["Tayang"])
        self.assertEqual(data["announcements"][0]["id"], live.id)
        self.assertEqual(data["announcements"][0]["level"], "INFO")
        self.assertIn("updated_at", data["announcements"][0])

    def test_no_store_cache_header(self):
        response = self.client.get(self.url)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_empty_when_nothing_live(self):
        response = self.client.get(self.url)
        self.assertEqual(json.loads(response.content), {"announcements": []})

    def test_ordered_by_priority_desc(self):
        _make(message="low", priority=1)
        _make(message="high", priority=10)
        data = json.loads(self.client.get(self.url).content)
        self.assertEqual(
            [a["message"] for a in data["announcements"]], ["high", "low"]
        )


class AnnouncementAdminTests(TestCase):
    def test_registered_on_custom_admin_site(self):
        from visits.admin import admin_site

        self.assertIn(Announcement, admin_site._registry)

    def test_status_badge_labels(self):
        from visits.admin import admin_site
        from .admin import AnnouncementAdmin

        ma = AnnouncementAdmin(Announcement, admin_site)
        self.assertIn("Tayang", ma.status_badge(_make()))
        self.assertIn("Nonaktif", ma.status_badge(_make(active=False)))
        self.assertIn(
            "Terjadwal",
            ma.status_badge(_make(start_offset_hours=1, end_offset_hours=2)),
        )
        self.assertIn(
            "Berakhir",
            ma.status_badge(_make(start_offset_hours=-2, end_offset_hours=-1)),
        )
