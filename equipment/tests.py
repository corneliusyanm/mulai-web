from django.core.cache import cache
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from . import guide
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
            "shorts": "https://www.youtube.com/shorts/abcdef123",
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
            "shorts": "https://www.youtube.com/shorts/abcdef123",
            "with_params": "https://www.youtube.com/watch?v=abcdef123&t=30s",
            "shorts_with_params": "https://www.youtube.com/shorts/abcdef123?feature=share",
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
            "https://www.youtube.com/shorts/tip4",
        ]
        equipment = Equipment(
            name="Test Equipment",
            video_link="https://www.youtube.com/watch?v=main123",
            additional_videos=additional_urls,
        )

        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 4)

        # Test first video data structure (standard watch URL)
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

        # Test shorts video processing
        shorts_video = video_data[3]
        self.assertEqual(shorts_video["url"], "https://www.youtube.com/shorts/tip4")
        self.assertEqual(shorts_video["video_id"], "tip4")
        self.assertEqual(
            shorts_video["embed_url"], "https://www.youtube.com/embed/tip4"
        )
        self.assertEqual(
            shorts_video["thumbnail_url"],
            "https://img.youtube.com/vi/tip4/hqdefault.jpg",
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
            "https://www.youtube.com/shorts/mno012": "mno012",
            "https://www.youtube.com/watch?v=xyz123&t=30s": "xyz123",
            "https://www.youtube.com/shorts/pqr345?feature=share": "pqr345",
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

    def test_youtube_shorts_url_conversion(self):
        """
        Test that YouTube Shorts URLs are properly converted to embed format.
        This tests the specific use case mentioned by the user.
        """
        # Test main video with shorts URL
        equipment = Equipment.objects.create(
            name="Test Equipment with Shorts",
            video_link="https://www.youtube.com/shorts/Dca_kc5ONOQ",
        )

        # Should extract video ID correctly
        self.assertEqual(equipment.get_youtube_video_id(), "Dca_kc5ONOQ")

        # Should generate correct embed URL
        expected_embed = "https://www.youtube.com/embed/Dca_kc5ONOQ"
        self.assertEqual(equipment.get_youtube_embed_url(), expected_embed)

        # Should generate correct thumbnail URL
        expected_thumbnail = "https://img.youtube.com/vi/Dca_kc5ONOQ/hqdefault.jpg"
        self.assertEqual(equipment.get_youtube_thumbnail_url(), expected_thumbnail)

        # Test additional videos with shorts URLs
        additional_shorts = [
            "https://www.youtube.com/shorts/abc123",
            "https://www.youtube.com/shorts/def456?feature=share",
        ]
        equipment.additional_videos = additional_shorts
        equipment.save()

        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 2)

        # Check first shorts video
        self.assertEqual(video_data[0]["video_id"], "abc123")
        self.assertEqual(
            video_data[0]["embed_url"], "https://www.youtube.com/embed/abc123"
        )

        # Check second shorts video (with parameters)
        self.assertEqual(video_data[1]["video_id"], "def456")
        self.assertEqual(
            video_data[1]["embed_url"], "https://www.youtube.com/embed/def456"
        )

    def test_urls_without_protocol_support(self):
        """
        Test that URLs without https:// protocol are automatically handled.
        """
        # Test main video without protocol
        equipment = Equipment.objects.create(
            name="Test Equipment No Protocol",
            video_link="youtube.com/watch?v=noproto123",
        )

        # Should extract video ID correctly
        self.assertEqual(equipment.get_youtube_video_id(), "noproto123")

        # Should generate correct embed URL
        expected_embed = "https://www.youtube.com/embed/noproto123"
        self.assertEqual(equipment.get_youtube_embed_url(), expected_embed)

        # Test additional videos without protocol
        additional_urls_no_protocol = [
            "www.youtube.com/watch?v=tip1",
            "youtu.be/tip2",
            "youtube.com/shorts/tip3",
            "www.youtube.com/embed/tip4",
        ]
        equipment.additional_videos = additional_urls_no_protocol
        equipment.save()

        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 4)

        # Check that all video IDs are extracted correctly
        expected_ids = ["tip1", "tip2", "tip3", "tip4"]
        for i, expected_id in enumerate(expected_ids):
            self.assertEqual(video_data[i]["video_id"], expected_id)
            self.assertEqual(
                video_data[i]["embed_url"],
                f"https://www.youtube.com/embed/{expected_id}",
            )

    def test_mixed_protocol_urls(self):
        """
        Test handling of mixed URLs - some with protocol, some without.
        """
        mixed_urls = [
            "https://www.youtube.com/watch?v=with_https",
            "youtube.com/shorts/without_https",
            "http://youtu.be/with_http",
            "www.youtube.com/embed/without_protocol",
        ]

        equipment = Equipment(
            name="Mixed Protocol Test",
            video_link="youtube.com/watch?v=main",
            additional_videos=mixed_urls,
        )

        # Test main video
        self.assertEqual(equipment.get_youtube_video_id(), "main")

        # Test additional videos processing
        video_data = equipment.get_additional_video_data()
        self.assertEqual(len(video_data), 4)

        expected_ids = ["with_https", "without_https", "with_http", "without_protocol"]
        for i, expected_id in enumerate(expected_ids):
            self.assertEqual(video_data[i]["video_id"], expected_id)

    def test_ensure_protocol_method(self):
        """
        Test the _ensure_protocol helper method directly.
        """
        equipment = Equipment(name="Test", video_link="dummy")

        test_cases = {
            # Already has protocol - should remain unchanged
            "https://youtube.com/watch?v=test": "https://youtube.com/watch?v=test",
            "http://youtu.be/test": "http://youtu.be/test",
            # Missing protocol - should add https://
            "youtube.com/watch?v=test": "https://youtube.com/watch?v=test",
            "www.youtube.com/shorts/test": "https://www.youtube.com/shorts/test",
            "youtu.be/test": "https://youtu.be/test",
            # Edge cases
            "": "",
            None: None,
        }

        for input_url, expected_url in test_cases.items():
            result = equipment._ensure_protocol(input_url)
            self.assertEqual(result, expected_url, f"Failed for input: {input_url}")


class EquipmentViewsTest(TestCase):
    def setUp(self):
        cache.clear()
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
        self.assertIn("Chest", [group["name"] for group in response.context["groups"]])

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
    """A view counts when the page reports it, not when the URL is fetched."""

    BROWSER = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"

    def setUp(self):
        self.equipment = Equipment.objects.create(
            name="Bench Press",
            muscle_group="Chest",
            video_link="https://www.youtube.com/watch?v=bench123",
        )
        self.detail = reverse("equipment:detail", kwargs={"slug": self.equipment.slug})
        self.seen = reverse("equipment:seen", kwargs={"slug": self.equipment.slug})

    def counts(self):
        self.equipment.refresh_from_db()
        return (
            self.equipment.total_views,
            self.equipment.authenticated_views,
            self.equipment.anonymous_views,
        )

    def test_fetching_the_page_alone_counts_nothing(self):
        response = self.client.get(self.detail, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_the_page_carries_the_counter_and_skips_automated_browsers(self):
        body = self.client.get(self.detail, HTTP_USER_AGENT=self.BROWSER).content.decode()

        self.assertIn(f'data-seen-url="{self.seen}"', body)
        self.assertIn("data-csrf=", body)
        self.assertIn("navigator.webdriver", body)
        self.assertIn("visibilityState === 'visible'", body)

    def test_a_reported_view_counts_as_anonymous(self):
        response = self.client.post(self.seen, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.counts(), (1, 0, 1))

    def test_a_reported_view_from_a_member_counts_as_theirs(self):
        session = self.client.session
        session["member_email"] = "test@example.com"
        session.save()

        self.client.post(self.seen, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(self.counts(), (1, 1, 0))

    def test_the_same_phone_counts_once_a_day(self):
        self.client.post(self.seen, HTTP_USER_AGENT=self.BROWSER)
        self.client.post(self.seen, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(self.counts(), (1, 0, 1))

    def test_a_bot_user_agent_is_still_not_counted(self):
        response = self.client.post(self.seen, HTTP_USER_AGENT="Googlebot/2.1")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_a_report_without_the_page_token_is_refused(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        response = strict.post(self.seen, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_a_report_with_the_page_token_is_accepted(self):
        import re as regex
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        body = strict.get(self.detail, HTTP_USER_AGENT=self.BROWSER).content.decode()
        token = regex.search(r'data-csrf="([^"]+)"', body).group(1)

        response = strict.post(self.seen, HTTP_USER_AGENT=self.BROWSER, HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.counts(), (1, 0, 1))

    def test_a_get_on_the_counter_is_not_allowed(self):
        response = self.client.get(self.seen, HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_an_unknown_machine_is_a_404(self):
        response = self.client.post(
            reverse("equipment:seen", kwargs={"slug": "tidak-ada"}), HTTP_USER_AGENT=self.BROWSER
        )

        self.assertEqual(response.status_code, 404)


class YouTubeEmbedReferrerPolicyTest(TestCase):
    """YouTube shows Error 153 on an embed whose page sends no Referer."""

    def setUp(self):
        cache.clear()
        self.equipment = Equipment.objects.create(
            name="Chest Press",
            muscle_group="Chest",
            video_link="https://www.youtube.com/watch?v=chest",
        )

    def test_pages_with_embeds_send_the_origin_to_other_sites(self):
        for url in (
            reverse("equipment:list"),
            reverse("equipment:detail", kwargs={"slug": self.equipment.slug}),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.headers["Referrer-Policy"],
                    "strict-origin-when-cross-origin",
                )


class GuideStepsTest(TestCase):
    """A description becomes an intro and numbered steps, losing nothing."""

    def test_an_intro_sentence_then_numbered_steps(self):
        split = guide.steps(
            "Mesin ini melatih paha. Duduk dulu. Dorong platformnya. Turunkan pelan-pelan."
        )

        self.assertEqual(split["intro"], "Mesin ini melatih paha.")
        self.assertEqual(split["steps"], ["Duduk dulu.", "Dorong platformnya.", "Turunkan pelan-pelan."])

    def test_an_instruction_first_is_step_one(self):
        split = guide.steps("Posisikan kaki di pijakan. Tarik handle. Kembali pelan.")

        self.assertEqual(split["intro"], "")
        self.assertEqual(len(split["steps"]), 3)

    def test_nothing_is_dropped(self):
        texts = [
            "Platform ini untuk squat, front squat, dll. Atur rack. Gunakan beban ringan.",
            "Alat ini\xa0melatih dada.  Duduk tegak.\nDorong ke depan! Tahan (2 detik). Lepas.",
        ]
        for text in texts:
            split = guide.steps(text)
            joined = " ".join(filter(None, [split["intro"]] + split["steps"]))
            self.assertEqual(joined, " ".join(text.replace("\xa0", " ").split()))

    def test_two_sentences_stay_a_paragraph(self):
        split = guide.steps("Alat ini melatih bahu. Duduk dan dorong ke atas.")

        self.assertEqual(split["steps"], [])
        self.assertEqual(split["intro"], "Alat ini melatih bahu. Duduk dan dorong ke atas.")

    def test_an_empty_description_has_nothing(self):
        self.assertEqual(guide.steps(""), {"intro": "", "steps": []})


class GuideGroupingTest(TestCase):
    def make(self, name, group, detail=""):
        return Equipment.objects.create(
            name=name, muscle_group=group, detailed_muscle_group=detail,
            video_link="https://www.youtube.com/watch?v=" + name.replace(" ", ""),
        )

    def test_groups_follow_the_page_order_and_skip_empty_ones(self):
        machines = [self.make("Lat Pulldown", "Punggung"), self.make("Leg Press", "Kaki")]

        groups = guide.grouped(machines)

        self.assertEqual([g["label"] for g in groups], ["Kaki", "Punggung"])
        self.assertEqual(groups[0]["id"], "kaki")

    def test_an_unknown_group_goes_last_as_typed_and_no_group_is_lainnya(self):
        machines = [self.make("Mat", "Perut"), self.make("Rope", ""), self.make("Leg Press", "Kaki")]

        labels = [g["label"] for g in guide.grouped(machines)]

        self.assertEqual(labels, ["Kaki", "Perut", "Lainnya"])

    def test_kardio_gets_a_short_label_and_a_stable_id(self):
        groups = guide.grouped([self.make("Treadmill", "Kardio (Jantung)")])

        self.assertEqual((groups[0]["label"], groups[0]["id"]), ("Kardio", "kardio-jantung"))

    def test_starter_keeps_its_order_and_skips_machines_that_are_missing(self):
        machines = [self.make("Leg Press", "Kaki"), self.make("Treadmill", "Kardio (Jantung)")]

        starter = guide.starter(machines)

        self.assertEqual([s["equipment"].slug for s in starter], ["treadmill", "leg-press"])
        self.assertEqual([s["position"] for s in starter], [1, 2])

    def test_target_muscles_are_split_and_a_repeat_of_the_group_is_dropped(self):
        press = self.make("Multi Press", "Bahu", "Bahu Depan, Dada Atas")
        bike = self.make("Sepeda Statis", "Kardio (Jantung)", "Kardio (Jantung)")

        self.assertEqual(guide.target_muscles(press), ["Bahu Depan", "Dada Atas"])
        self.assertEqual(guide.target_muscles(bike), [])


class PanduanAlatListPageTest(TestCase):
    def setUp(self):
        # the list is behind cache_page, and LocMemCache outlives a test
        cache.clear()
        self.press = Equipment.objects.create(
            name="Leg Press", muscle_group="Kaki", detailed_muscle_group="Seluruh kaki",
            video_link="https://www.youtube.com/watch?v=legpress",
        )
        self.run = Equipment.objects.create(
            name="Treadmill", muscle_group="Kardio (Jantung)",
            video_link="https://www.youtube.com/watch?v=tread",
        )

    def tearDown(self):
        cache.clear()

    def test_every_machine_is_a_card_linking_to_its_page(self):
        response = self.client.get(reverse("equipment:list"))

        for machine in (self.press, self.run):
            self.assertContains(response, f'href="{reverse("equipment:detail", args=[machine.slug])}"')

    def test_the_list_loads_no_video_player(self):
        response = self.client.get(reverse("equipment:list"))

        self.assertNotContains(response, "<iframe")

    def test_the_starter_set_shows_what_exists_in_order(self):
        response = self.client.get(reverse("equipment:list"))

        self.assertContains(response, "Mulai dari sini")
        starter = response.context["starter"]
        self.assertEqual([s["equipment"].slug for s in starter], ["treadmill", "leg-press"])

    def test_the_body_map_only_links_groups_that_have_machines(self):
        response = self.client.get(reverse("equipment:list"))

        self.assertContains(response, 'href="#grp-kaki" data-group="kaki" aria-label="Kaki, 1 alat"', count=2)
        self.assertNotContains(response, 'href="#grp-punggung"')

    def test_it_says_how_many_machines_there_are(self):
        response = self.client.get(reverse("equipment:list"))

        self.assertContains(response, "2 alat di Mulai Gym, semua ada video tutorialnya")
        self.assertContains(response, "<title>Panduan Alat Gym untuk Pemula | Mulai Gym</title>")


class PanduanAlatDetailPageTest(TestCase):
    def setUp(self):
        self.press = Equipment.objects.create(
            name="Leg Press", muscle_group="Kaki", detailed_muscle_group="Paha, Pantat",
            description="Mesin ini melatih paha. Duduk dulu. Dorong platformnya. Turunkan pelan-pelan.",
            video_link="https://www.youtube.com/watch?v=legpress",
            additional_videos=["https://youtu.be/tip1"],
        )
        self.curl = Equipment.objects.create(
            name="Leg Curl", muscle_group="Kaki", video_link="https://www.youtube.com/watch?v=curl"
        )
        self.row = Equipment.objects.create(
            name="Cable Row", muscle_group="Punggung", video_link="https://www.youtube.com/watch?v=row"
        )

    def get(self, machine):
        return self.client.get(reverse("equipment:detail", args=[machine.slug]))

    def test_the_title_is_what_people_search_for(self):
        response = self.get(self.press)

        self.assertContains(response, "<title>Cara Pakai Leg Press untuk Pemula | Mulai Gym</title>")
        self.assertContains(response, '<meta name="description" content="Mesin ini melatih paha.">')

    def test_the_steps_are_a_numbered_list(self):
        response = self.get(self.press)

        self.assertContains(response, '<ol class="alat-steps">')
        self.assertContains(response, "<li>Dorong platformnya.</li>")

    def test_one_player_and_the_tips_as_thumbnails(self):
        response = self.get(self.press)

        self.assertContains(response, "<iframe", count=1)
        self.assertContains(response, 'data-embed="https://www.youtube.com/embed/tip1"')
        self.assertContains(response, "Tips 1")

    def test_related_machines_share_the_group_and_leave_this_one_out(self):
        related = self.get(self.press).context["related"]

        self.assertEqual(related, [self.curl])

    def test_the_target_muscles_are_chips(self):
        response = self.get(self.press)

        self.assertEqual(response.context["targets"], ["Paha", "Pantat"])


class NotEveryLinkIsAVideoTest(TestCase):
    """A machine whose link is not a YouTube video has no player and no thumbnail."""

    def setUp(self):
        cache.clear()
        Equipment.objects.create(name="Leg Press", muscle_group="Kaki", video_link="https://www.youtube.com/watch?v=abc")
        Equipment.objects.create(name="Rowing", muscle_group="Kaki", video_link="https://www.instagram.com/reel/xyz/")

    def tearDown(self):
        cache.clear()

    def test_the_list_does_not_claim_every_machine_has_a_video(self):
        response = self.client.get(reverse("equipment:list"))

        self.assertContains(response, "2 alat di Mulai Gym.")
        self.assertNotContains(response, "semua ada video")

    def test_no_broken_thumbnail_is_printed(self):
        for url in (reverse("equipment:list"), reverse("equipment:detail", args=["leg-press"])):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), 'src="None"')

