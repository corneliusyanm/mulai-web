from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import ReviewSummary, Testimonial


class ReviewSummaryTest(TestCase):
    def test_seeded_from_the_listing(self):
        """The migration ships the numbers from the Google Maps listing."""
        summary = ReviewSummary.get_solo()

        self.assertIsNotNone(summary)
        self.assertEqual(str(summary.rating), "5.0")
        self.assertEqual(summary.review_count, 142)
        self.assertIn("maps.app.goo.gl", summary.maps_url)

    def test_rating_reads_the_indonesian_way(self):
        summary = ReviewSummary.get_solo()

        self.assertEqual(summary.rating_display, "5,0")

    def test_get_solo_returns_nothing_when_empty(self):
        ReviewSummary.objects.all().delete()

        self.assertIsNone(ReviewSummary.get_solo())


class TestimonialModelTest(TestCase):
    def test_initial_and_stars(self):
        review = Testimonial.objects.create(
            author_name="  siti nurhaliza", rating=4, text="Nyaman"
        )

        self.assertEqual(review.initial, "S")
        self.assertEqual(len(list(review.stars)), 4)

    def test_active_ordering_is_priority_then_newest(self):
        first = Testimonial.objects.create(
            author_name="A", text="satu", priority=0
        )
        pinned = Testimonial.objects.create(
            author_name="B", text="dua", priority=10
        )
        newer = Testimonial.objects.create(
            author_name="C", text="tiga", priority=0
        )
        Testimonial.objects.create(
            author_name="D", text="empat", is_active=False, priority=99
        )

        active = list(Testimonial.get_active())

        self.assertEqual(active, [pinned, newer, first])


class HomepageReviewsSectionTest(TestCase):
    def test_badge_renders_from_the_summary(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Kata Member Mulai")
        self.assertContains(response, "5,0")
        self.assertContains(response, "142 ulasan di Google")
        self.assertContains(response, "maps.app.goo.gl")

    def test_reviews_render_with_author_and_text(self):
        Testimonial.objects.create(
            author_name="Rizky",
            text="Tempatnya nyaman dan trainernya sabar banget buat pemula.",
            review_url="https://maps.google.com/review/abc",
        )

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Rizky")
        self.assertContains(response, "trainernya sabar banget")
        self.assertContains(response, "Lihat di Google")

    def test_hidden_reviews_do_not_render(self):
        Testimonial.objects.create(
            author_name="Rahasia", text="jangan tampil", is_active=False
        )

        response = self.client.get(reverse("home"))

        self.assertNotContains(response, "Rahasia")

    def test_capped_at_six(self):
        for i in range(9):
            Testimonial.objects.create(author_name=f"Member {i}", text=f"ulasan {i}")

        response = self.client.get(reverse("home"))

        self.assertEqual(len(response.context["testimonials"]), 6)

    def test_whole_section_disappears_without_content(self):
        ReviewSummary.objects.all().delete()

        response = self.client.get(reverse("home"))

        self.assertNotContains(response, "Kata Member Mulai")

    def test_review_text_keeps_its_line_breaks_escaped(self):
        Testimonial.objects.create(
            author_name="Budi", text="Bagus <script>alert(1)</script>"
        )

        response = self.client.get(reverse("home"))

        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")


class HomepageInstagramSectionTest(TestCase):
    TILES = [
        {
            "image": "images/logo_white.png",
            "alt": "Logo Mulai Gym",
            "post_url": "https://www.instagram.com/p/ABC123/",
        },
        {"image": "images/wave.png", "alt": "Ombak"},
    ]

    def test_hidden_while_no_tiles_are_configured(self):
        response = self.client.get(reverse("home"))

        self.assertNotContains(response, 'id="instagram"')
        self.assertEqual(response.context["instagram_tiles"], [])

    @patch("accounts.views.get_tiles")
    def test_tiles_render_and_link(self, get_tiles):
        get_tiles.return_value = self.TILES

        response = self.client.get(reverse("home"))

        self.assertContains(response, 'id="instagram"')
        self.assertContains(response, "@mulaigym.id")
        self.assertContains(response, "https://www.instagram.com/p/ABC123/")
        self.assertContains(response, "Logo Mulai Gym")
        self.assertContains(response, "Lihat Semua")
        # lazy, so the grid costs nothing until it is scrolled to
        self.assertContains(response, 'loading="lazy"')

    @patch("accounts.views.get_tiles")
    def test_tile_without_a_post_url_falls_back_to_the_profile(self, get_tiles):
        get_tiles.return_value = [self.TILES[1]]

        response = self.client.get(reverse("home"))

        self.assertContains(response, "instagram.com/mulaigym.id")
        self.assertNotContains(response, "/p/ABC123/")

    def test_grid_is_capped_at_nine(self):
        from .instagram import get_tiles

        tile = {"image": "images/logo_white.png", "alt": "Logo"}
        with patch("homepage.instagram.INSTAGRAM_TILES", [tile] * 20):
            self.assertEqual(len(get_tiles()), 9)

    def test_every_configured_tile_points_at_a_real_file(self):
        """A bad path would raise inside {% static %} in production."""
        from django.contrib.staticfiles import finders

        from .instagram import INSTAGRAM_TILES

        for tile in INSTAGRAM_TILES:
            with self.subTest(image=tile["image"]):
                self.assertIsNotNone(
                    finders.find(tile["image"]),
                    f"{tile['image']} is not in static/, the homepage would 500",
                )
                self.assertTrue(tile.get("alt"), "every tile needs alt text")

    def test_a_missing_file_drops_its_tile_instead_of_breaking_the_page(self):
        from .instagram import get_tiles

        good = {"image": "images/logo_white.png", "alt": "Logo"}
        broken = {"image": "images/instagram/does-not-exist.jpg", "alt": "Hilang"}
        with patch("homepage.instagram.INSTAGRAM_TILES", [good, broken]):
            self.assertEqual(get_tiles(), [good])

        with patch("accounts.views.get_tiles", return_value=[good]):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "does-not-exist")
