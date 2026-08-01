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
