from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from .models import Equipment
from .views import is_likely_bot, should_count_view
import time


class EquipmentModelTest(TestCase):
    def test_equipment_creation(self):
        """
        Test that an Equipment object is created with a slug.
        """
        equipment = Equipment.objects.create(
            name="Test Lat Pulldown",
            video_link="https://www.youtube.com/watch?v=12345",
        )
        self.assertEqual(equipment.name, "Test Lat Pulldown")
        self.assertEqual(equipment.slug, "test-lat-pulldown")

    def test_youtube_embed_url(self):
        """
        Test the get_youtube_embed_url method with different URL formats.
        """
        urls = {
            "standard": "https://www.youtube.com/watch?v=abcdef123",
            "shortened": "https://youtu.be/abcdef123",
            "embed": "https://www.youtube.com/embed/abcdef123",
        }
        expected_url = "https://www.youtube.com/embed/abcdef123"

        for name, url in urls.items():
            equipment = Equipment(name=name, video_link=url)
            self.assertEqual(equipment.get_youtube_embed_url(), expected_url)

    def test_youtube_video_id_extraction(self):
        """
        Test the get_youtube_video_id method with different URL formats.
        """
        urls = {
            "standard": "https://www.youtube.com/watch?v=abcdef123",
            "shortened": "https://youtu.be/abcdef123",
            "embed": "https://www.youtube.com/embed/abcdef123",
            "with_params": "https://www.youtube.com/watch?v=abcdef123&t=30s",
        }
        expected_id = "abcdef123"

        for name, url in urls.items():
            equipment = Equipment(name=name, video_link=url)
            self.assertEqual(equipment.get_youtube_video_id(), expected_id)

    def test_youtube_thumbnail_url(self):
        """
        Test the get_youtube_thumbnail_url method.
        """
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=abcdef123",
        )

        # Test default quality
        expected_default = "https://img.youtube.com/vi/abcdef123/hqdefault.jpg"
        self.assertEqual(equipment.get_youtube_thumbnail_url(), expected_default)

        # Test specific quality
        expected_maxres = "https://img.youtube.com/vi/abcdef123/maxresdefault.jpg"
        self.assertEqual(
            equipment.get_youtube_thumbnail_url("maxresdefault"), expected_maxres
        )

    def test_additional_videos_default(self):
        """
        Test that additional_videos field defaults to empty list.
        """
        equipment = Equipment.objects.create(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
        )
        self.assertEqual(equipment.additional_videos, [])

    def test_additional_videos_storage(self):
        """
        Test that additional_videos field can store multiple URLs.
        """
        urls = [
            "https://www.youtube.com/watch?v=tip1",
            "https://youtu.be/tip2",
            "https://www.youtube.com/embed/tip3",
        ]
        equipment = Equipment.objects.create(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
            additional_videos=urls,
        )
        self.assertEqual(equipment.additional_videos, urls)

    def test_get_additional_video_data_empty(self):
        """
        Test get_additional_video_data returns empty list when no additional videos.
        """
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
        )
        self.assertEqual(equipment.get_additional_video_data(), [])

    def test_get_additional_video_data_with_videos(self):
        """
        Test get_additional_video_data processes URLs correctly.
        """
        additional_urls = [
            "https://www.youtube.com/watch?v=tip1",
            "https://youtu.be/tip2",
            "https://www.youtube.com/embed/tip3",
        ]
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
            additional_videos=additional_urls,
        )

        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 3)

        # Test first video data structure
        first_video = video_data[0]
        self.assertIn("url", first_video)
        self.assertIn("video_id", first_video)
        self.assertIn("embed_url", first_video)
        self.assertIn("thumbnail_url", first_video)

        self.assertEqual(first_video["url"], "https://www.youtube.com/watch?v=tip1")
        self.assertEqual(first_video["video_id"], "tip1")
        self.assertEqual(first_video["embed_url"], "https://www.youtube.com/embed/tip1")
        self.assertEqual(
            first_video["thumbnail_url"],
            "https://img.youtube.com/vi/tip1/hqdefault.jpg",
        )

    def test_get_additional_video_data_filters_invalid(self):
        """
        Test that invalid URLs are filtered out from additional video data.
        """
        additional_urls = [
            "https://www.youtube.com/watch?v=valid1",
            "",  # Empty string
            "not a url",  # Invalid URL
            "https://vimeo.com/123456",  # Non-YouTube URL
            "https://youtu.be/valid2",
        ]
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
            additional_videos=additional_urls,
        )

        video_data = equipment.get_additional_video_data()
        # Should only return the 2 valid YouTube URLs
        self.assertEqual(len(video_data), 2)
        self.assertEqual(video_data[0]["video_id"], "valid1")
        self.assertEqual(video_data[1]["video_id"], "valid2")

    def test_extract_youtube_video_id_method(self):
        """
        Test the private _extract_youtube_video_id method with different URL formats.
        """
        equipment = Equipment(
            name="Test", video_link="https://www.youtube.com/watch?v=dummy"
        )

        test_urls = {
            "https://www.youtube.com/watch?v=abc123": "abc123",
            "https://youtu.be/def456": "def456",
            "https://www.youtube.com/embed/ghi789": "ghi789",
            "https://www.youtube.com/watch?v=xyz123&t=30s": "xyz123",
            "": None,
            None: None,
        }

        for url, expected_id in test_urls.items():
            result = equipment._extract_youtube_video_id(url)
            self.assertEqual(result, expected_id, f"Failed for URL: {url}")

    def test_additional_videos_in_template_context(self):
        """
        Test that additional videos are available in detail view context.
        """
        additional_urls = [
            "https://www.youtube.com/watch?v=tip1",
            "https://youtu.be/tip2",
        ]
        equipment = Equipment.objects.create(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
            additional_videos=additional_urls,
        )

        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": equipment.slug})
        )
        self.assertEqual(response.status_code, 200)

        # Check that additional video data is accessible in template
        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 2)


class EquipmentViewsTest(TestCase):
    def setUp(self):
        self.equipment1 = Equipment.objects.create(
            name="Chest Press",
            muscle_group="Chest",
            video_link="https://www.youtube.com/watch?v=chest",
        )
        self.equipment2 = Equipment.objects.create(
            name="Bicep Curl",
            muscle_group="Arms",
            video_link="https://www.youtube.com/watch?v=bicep",
        )

    def test_equipment_list_view(self):
        """
        Test the equipment list view.
        """
        response = self.client.get(reverse("equipment:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chest Press")
        self.assertContains(response, "Bicep Curl")
        self.assertIn("grouped_equipments", response.context)
        self.assertIn("Chest", response.context["grouped_equipments"])

    def test_equipment_detail_view(self):
        """
        Test the equipment detail view.
        """
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment1.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chest Press")

    def test_equipment_detail_view_not_found(self):
        """
        Test that the detail view returns a 404 for a non-existent slug.
        """
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": "non-existent-slug"})
        )
        self.assertEqual(response.status_code, 404)


class EquipmentAnalyticsTest(TestCase):
    def setUp(self):
        self.equipment = Equipment.objects.create(
            name="Test Equipment",
            muscle_group="Test",
            video_link="https://www.youtube.com/watch?v=test123",
        )
        self.factory = RequestFactory()

    def test_initial_view_counts(self):
        """Test that equipment is created with zero view counts."""
        self.assertEqual(self.equipment.total_views, 0)
        self.assertEqual(self.equipment.authenticated_views, 0)
        self.assertEqual(self.equipment.anonymous_views, 0)

    def test_increment_view_count_authenticated(self):
        """Test incrementing view count for authenticated users."""
        self.equipment.increment_view_count(is_authenticated=True)

        # Refresh from database
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.total_views, 1)
        self.assertEqual(self.equipment.authenticated_views, 1)
        self.assertEqual(self.equipment.anonymous_views, 0)

    def test_increment_view_count_anonymous(self):
        """Test incrementing view count for anonymous users."""
        self.equipment.increment_view_count(is_authenticated=False)

        # Refresh from database
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.total_views, 1)
        self.assertEqual(self.equipment.authenticated_views, 0)
        self.assertEqual(self.equipment.anonymous_views, 1)

    def test_increment_view_count_multiple(self):
        """Test multiple view count increments."""
        # 2 authenticated views
        self.equipment.increment_view_count(is_authenticated=True)
        self.equipment.increment_view_count(is_authenticated=True)

        # 3 anonymous views
        self.equipment.increment_view_count(is_authenticated=False)
        self.equipment.increment_view_count(is_authenticated=False)
        self.equipment.increment_view_count(is_authenticated=False)

        # Refresh from database
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.total_views, 5)
        self.assertEqual(self.equipment.authenticated_views, 2)
        self.assertEqual(self.equipment.anonymous_views, 3)


class BotDetectionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_bot_detection_common_bots(self):
        """Test detection of common bot user agents."""
        bot_user_agents = [
            "Googlebot/2.1",
            "Mozilla/5.0 (compatible; bingbot/2.0)",
            "facebookexternalhit/1.1",
            "Twitterbot/1.0",
            "python-requests/2.25.1",
            "curl/7.68.0",
            "Wget/1.20.3",
            "bot crawler spider",
            "scrapy/2.5.0",
        ]

        for user_agent in bot_user_agents:
            request = self.factory.get("/")
            request.META["HTTP_USER_AGENT"] = user_agent
            self.assertTrue(
                is_likely_bot(request), f"Failed to detect bot: {user_agent}"
            )

    def test_bot_detection_legitimate_browsers(self):
        """Test that legitimate browser user agents are not flagged as bots."""
        legitimate_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]

        for user_agent in legitimate_user_agents:
            request = self.factory.get("/")
            request.META["HTTP_USER_AGENT"] = user_agent
            self.assertFalse(
                is_likely_bot(request), f"Incorrectly flagged as bot: {user_agent}"
            )

    def test_bot_detection_short_user_agent(self):
        """Test that suspiciously short user agents are flagged as bots."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "short"  # Less than 10 characters
        self.assertTrue(is_likely_bot(request))

    def test_bot_detection_missing_user_agent(self):
        """Test that missing user agent is flagged as bot."""
        request = self.factory.get("/")
        # Don't set HTTP_USER_AGENT
        self.assertTrue(is_likely_bot(request))


class ViewCountingLogicTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.equipment = Equipment.objects.create(
            name="Test Equipment",
            muscle_group="Test",
            video_link="https://www.youtube.com/watch?v=test123",
        )

    def add_session_to_request(self, request):
        """Helper method to add session support to request."""
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

    def test_should_count_view_normal_user(self):
        """Test that normal users get their views counted."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Chrome/91.0) Normal Browser"
        self.add_session_to_request(request)

        result = should_count_view(request, self.equipment.slug)
        self.assertTrue(result)

    def test_should_count_view_bot_user(self):
        """Test that bot users don't get their views counted."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Googlebot/2.1"
        self.add_session_to_request(request)

        result = should_count_view(request, self.equipment.slug)
        self.assertFalse(result)

    def test_should_count_view_time_based_deduplication(self):
        """Test time-based deduplication with custom cooldown."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Chrome/91.0) Normal Browser"
        self.add_session_to_request(request)

        # First view should be counted
        result1 = should_count_view(request, self.equipment.slug, cooldown_hours=1)
        self.assertTrue(result1)

        # Second view within cooldown should not be counted
        result2 = should_count_view(request, self.equipment.slug, cooldown_hours=1)
        self.assertFalse(result2)

    def test_should_count_view_after_cooldown(self):
        """Test that views are counted again after cooldown expires."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Chrome/91.0) Normal Browser"
        self.add_session_to_request(request)

        # Set a very short cooldown for testing
        result1 = should_count_view(
            request, self.equipment.slug, cooldown_hours=0.001
        )  # ~3.6 seconds
        self.assertTrue(result1)

        # Simulate time passing by manually setting an old timestamp
        session_key = f"viewed_equipment_{self.equipment.slug}_last_time"
        old_time = time.time() - (0.001 * 60 * 60) - 1  # Just past cooldown
        request.session[session_key] = old_time

        # View should be counted again
        result2 = should_count_view(request, self.equipment.slug, cooldown_hours=0.001)
        self.assertTrue(result2)

    def test_should_count_view_different_equipment(self):
        """Test that different equipment can be viewed by same user."""
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Chrome/91.0) Normal Browser"
        self.add_session_to_request(request)

        equipment2 = Equipment.objects.create(
            name="Another Equipment",
            muscle_group="Test",
            video_link="https://www.youtube.com/watch?v=test456",
        )

        # Both should be counted
        result1 = should_count_view(request, self.equipment.slug)
        result2 = should_count_view(request, equipment2.slug)

        self.assertTrue(result1)
        self.assertTrue(result2)


class EquipmentDetailViewAnalyticsTest(TestCase):
    def setUp(self):
        self.equipment = Equipment.objects.create(
            name="Bench Press",
            muscle_group="Chest",
            video_link="https://www.youtube.com/watch?v=bench123",
        )

    def test_equipment_detail_view_increments_anonymous_count(self):
        """Test that visiting equipment detail increments anonymous view count."""
        # Simulate anonymous user
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
            HTTP_USER_AGENT="Mozilla/5.0 (Chrome/91.0) Normal Browser",
        )

        self.assertEqual(response.status_code, 200)

        # Refresh from database
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.total_views, 1)
        self.assertEqual(self.equipment.anonymous_views, 1)
        self.assertEqual(self.equipment.authenticated_views, 0)

    def test_equipment_detail_view_increments_authenticated_count(self):
        """Test that visiting equipment detail increments authenticated view count."""
        # Simulate authenticated member by setting session
        session = self.client.session
        session["member_email"] = "test@example.com"
        session.save()

        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
            HTTP_USER_AGENT="Mozilla/5.0 (Chrome/91.0) Normal Browser",
        )

        self.assertEqual(response.status_code, 200)

        # Refresh from database
        self.equipment.refresh_from_db()

        self.assertEqual(self.equipment.total_views, 1)
        self.assertEqual(self.equipment.authenticated_views, 1)
        self.assertEqual(self.equipment.anonymous_views, 0)

    def test_equipment_detail_view_bot_not_counted(self):
        """Test that bot visits are not counted."""
        response = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
            HTTP_USER_AGENT="Googlebot/2.1",
        )

        self.assertEqual(response.status_code, 200)

        # Refresh from database
        self.equipment.refresh_from_db()

        # Should remain at 0 since bot visit was not counted
        self.assertEqual(self.equipment.total_views, 0)
        self.assertEqual(self.equipment.authenticated_views, 0)
        self.assertEqual(self.equipment.anonymous_views, 0)

    def test_equipment_detail_view_duplicate_not_counted(self):
        """Test that duplicate visits within cooldown are not counted."""
        # First visit
        response1 = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
            HTTP_USER_AGENT="Mozilla/5.0 (Chrome/91.0) Normal Browser",
        )
        self.assertEqual(response1.status_code, 200)

        # Second visit (should not be counted due to session tracking)
        response2 = self.client.get(
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
            HTTP_USER_AGENT="Mozilla/5.0 (Chrome/91.0) Normal Browser",
        )
        self.assertEqual(response2.status_code, 200)

        # Refresh from database
        self.equipment.refresh_from_db()

        # Should only count once
        self.assertEqual(self.equipment.total_views, 1)
        self.assertEqual(self.equipment.anonymous_views, 1)
        self.assertEqual(self.equipment.authenticated_views, 0)
