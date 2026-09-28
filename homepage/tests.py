import json
import re
from datetime import date, time
from unittest.mock import patch
from xml.etree import ElementTree

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.db import OperationalError, ProgrammingError
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Member
from classes.models import Class, ClassInstance, ClassReview, ClassSchedule
from equipment.models import Equipment
from visits import busy_hours

from . import business, content, seo, stats
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



class HomepageSurvivesMissingTablesTest(TestCase):
    """Deploy runs migrations after the container is already serving traffic.

    In that window the homepage would be querying tables the release has not
    created yet, which is exactly how production went down once.
    """

    def test_homepage_still_renders_when_the_tables_are_missing(self):
        from django.db import ProgrammingError

        with patch.object(
            ReviewSummary, "get_solo", side_effect=ProgrammingError("no such table")
        ):
            with self.assertLogs("accounts.views", level="WARNING"):
                response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["review_summary"])
        self.assertEqual(response.context["testimonials"], [])
        self.assertNotContains(response, "Kata Member Mulai")
        # the rest of the page is untouched
        self.assertContains(response, "Belum pernah")
        self.assertContains(response, "Chat dulu, tanya-tanya gratis")

    def test_homepage_still_renders_when_the_connection_dies(self):
        from django.db import OperationalError

        with patch.object(
            Testimonial, "get_active", side_effect=OperationalError("gone")
        ):
            with self.assertLogs("accounts.views", level="WARNING"):
                response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)


class OpeningHoursTest(TestCase):
    def test_weekdays_with_the_same_hours_fold_into_one_row(self):
        self.assertEqual(
            business.opening_hours_rows(),
            [
                ("Senin - Jumat", "07:00 - 21:00"),
                ("Sabtu", "07:00 - 20:00"),
                ("Minggu", "07:30 - 20:00"),
            ],
        )

    def test_jam_kosong_reads_the_same_hours(self):
        # Sunday opens 07:30, so its first bar is still the 07:00 hour
        self.assertEqual(busy_hours.OPENING_HOURS[0], (7, 21))
        self.assertEqual(busy_hours.OPENING_HOURS[5], (7, 20))
        self.assertEqual(busy_hours.OPENING_HOURS[6], (7, 20))


class FreshCacheMixin:
    """The homepage numbers are cached, so every test starts from a cold cache."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()


class SiteSeoTest(FreshCacheMixin, TestCase):
    """What every page tells search engines, from base.html and context_processors.seo."""

    def _body(self, url, **extra):
        response = self.client.get(url, **extra)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_pages_are_declared_indonesian(self):
        self.assertIn('<html lang="id">', self._body(reverse("equipment:list")))

    def test_canonical_is_the_bare_domain_even_from_www(self):
        body = self._body(reverse("home"), HTTP_HOST="www.mulaigym.id")

        self.assertIn('<link rel="canonical" href="https://mulaigym.id/">', body)
        self.assertIn('<meta property="og:url" content="https://mulaigym.id/">', body)

    def test_every_page_gets_its_own_canonical(self):
        body = self._body(reverse("equipment:list"))

        self.assertIn('<link rel="canonical" href="https://mulaigym.id/alat/">', body)

    def test_a_page_without_its_own_description_gets_the_default(self):
        # the login page has no description of its own
        body = self._body(reverse("member_login"))

        description = re.search(r'<meta name="description" content="([^"]+)"', body).group(1)
        self.assertIn("pemula di Bandung", description)

    def test_the_landmark_keeps_its_capitals_mid_sentence(self):
        # the login page has no description of its own
        body = self._body(reverse("member_login"))

        self.assertIn("seberang SMPK 5 BPK Penabur", body)
        self.assertNotIn("smpk", body)

    def test_share_preview_image_is_an_absolute_https_url(self):
        body = self._body(reverse("equipment:list"))

        image = re.search(r'<meta property="og:image" content="([^"]+)"', body).group(1)
        self.assertTrue(image.startswith("https://mulaigym.id/static/"))

    def test_the_share_image_exists(self):
        self.assertIsNotNone(finders.find(seo.SHARE_IMAGE))

    def test_a_missing_share_image_drops_the_preview_instead_of_the_page(self):
        with patch("homepage.seo.static", side_effect=ValueError("not in manifest")):
            with self.assertLogs("homepage.seo", level="ERROR"):
                body = self._body(reverse("equipment:list"))

        self.assertNotIn('property="og:image"', body)

    def test_the_side_menu_has_no_whatsapp_button(self):
        body = self._body(reverse("equipment:list"))

        self.assertNotIn("wa.me", body)


class SitemapAndRobotsTest(TestCase):
    NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def test_sitemap_lists_the_public_pages_on_the_bare_domain(self):
        Equipment.objects.create(name="Leg Press", video_link="https://youtu.be/abc")

        response = self.client.get("/sitemap.xml", HTTP_HOST="www.mulaigym.id")

        self.assertEqual(response.status_code, 200)
        locs = [el.text for el in ElementTree.fromstring(response.content).findall("sm:url/sm:loc", self.NS)]
        self.assertIn("https://mulaigym.id/", locs)
        self.assertIn("https://mulaigym.id/alat/leg-press/", locs)
        self.assertIn("https://mulaigym.id/gizi/kalori/", locs)
        self.assertTrue(all(loc.startswith("https://mulaigym.id/") for loc in locs))
        self.assertFalse(any("/akun" in loc or "/admin" in loc for loc in locs))

    def test_every_sitemap_page_actually_loads(self):
        Equipment.objects.create(name="Leg Press", video_link="https://youtu.be/abc")
        body = self.client.get("/sitemap.xml").content

        for loc in ElementTree.fromstring(body).findall("sm:url/sm:loc", self.NS):
            path = loc.text.replace("https://mulaigym.id", "")
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_robots_points_at_the_sitemap_and_keeps_private_pages_out(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        text = response.content.decode()
        self.assertIn("Sitemap: https://mulaigym.id/sitemap.xml", text)
        self.assertIn("Disallow: /admin/", text)
        self.assertIn("Disallow: /akun/", text)


def make_member(i, *, pemula=True, gender="F"):
    return Member.objects.create(
        name=f"Member {i}",
        email=f"member{i}@example.com",
        phone_number=f"6281200{i:05d}",
        gender=gender,
        age=25,
        height=160,
        weight=55,
        years_of_working_out="belum pernah" if pemula else "2 tahun",
        goals="sehat",
        know_mulai_gym_from="instagram",
        is_pemula=pemula,
    )


class ShareInWordsTest(TestCase):
    def test_three_quarters_reads_as_3_dari_4(self):
        self.assertEqual(stats.share_in_words(644, 861), "3 dari 4")

    def test_a_half_reads_as_separuh(self):
        self.assertEqual(stats.share_in_words(50, 100), "separuh")

    def test_a_share_that_is_not_near_a_quarter_is_a_percentage(self):
        self.assertEqual(stats.share_in_words(62, 100), "62%")

    def test_the_tolerance_is_tight(self):
        # 70% is not "3 dari 4", it would be a small lie on the first line of the page
        self.assertEqual(stats.share_in_words(70, 100), "70%")

    def test_nothing_to_say_without_members(self):
        self.assertIsNone(stats.share_in_words(0, 0))



class HomepageStatsTest(FreshCacheMixin, TestCase):
    def test_share_of_first_timers_comes_from_the_members(self):
        for i in range(60):
            make_member(i, pemula=i < 45)

        self.assertEqual(stats.homepage_stats()["pemula_share"], "3 dari 4")

    def test_too_few_members_makes_no_claim(self):
        for i in range(stats.MIN_MEMBERS - 1):
            make_member(i)

        result = stats.homepage_stats()

        self.assertIsNone(result["pemula_share"])
        self.assertIsNone(result["female_percent"])

    def _scheduled(self, name, max_members):
        kelas = Class.objects.create(name=name, max_members=max_members)
        ClassSchedule.objects.create(
            class_obj=kelas, day_of_week=0, start_time=time(7, 15), end_time=time(8, 15)
        )
        return kelas

    def test_class_sizes_come_from_the_classes(self):
        self._scheduled("Kelas Pemula (Push)", 6)
        self._scheduled("Kelas Pemula (Pull)", 6)
        self._scheduled("Semi Private", 4)

        result = stats.homepage_stats()

        self.assertEqual(result["pemula_class_size"], 6)
        self.assertEqual(result["semi_private_size"], 4)

    def test_a_retired_class_does_not_set_the_size(self):
        self._scheduled("Kelas Pemula (Push)", 6)
        # an old one-off class with no schedule left, at the model default of 10
        Class.objects.create(name="Kelas Pemula Ramadan", max_members=10)

        self.assertEqual(stats.homepage_stats()["pemula_class_size"], 6)

    def test_unanswered_is_pemula_does_not_count_against_the_share(self):
        for i in range(60):
            make_member(i, pemula=i < 45)
        for i in range(60, 90):
            Member.objects.filter(pk=make_member(i).pk).update(is_pemula=None)

        self.assertEqual(stats.homepage_stats()["pemula_share"], "3 dari 4")

    def test_a_minority_of_first_timers_is_not_advertised(self):
        for i in range(60):
            make_member(i, pemula=i < 15)

        self.assertIsNone(stats.homepage_stats()["pemula_share"])

    def test_a_low_share_of_women_is_not_advertised(self):
        for i in range(60):
            make_member(i, gender="F" if i < 12 else "M")

        self.assertIsNone(stats.homepage_stats()["female_percent"])

    def test_no_classes_means_no_class_size(self):
        self.assertIsNone(stats.homepage_stats()["pemula_class_size"])

    def _reviews(self, count, mantap):
        kelas = Class.objects.create(name="Kelas Pemula (Push)", max_members=6)
        schedule = ClassSchedule.objects.create(
            class_obj=kelas, day_of_week=0, start_time=time(7, 15), end_time=time(8, 15)
        )
        instance = ClassInstance.objects.create(
            class_schedule=schedule,
            date=date(2026, 9, 7),
            start_time=time(7, 15),
            end_time=time(8, 15),
        )
        for i in range(count):
            ClassReview.objects.create(
                member=make_member(i),
                class_instance=instance,
                rating=ClassReview.MANTAP if i < mantap else ClassReview.OKE,
            )

    def test_mantap_share_from_the_class_ratings(self):
        self._reviews(stats.MIN_CLASS_REVIEWS, mantap=47)

        self.assertEqual(stats.homepage_stats()["mantap_percent"], 94)

    def test_a_weak_mantap_share_is_not_advertised(self):
        self._reviews(stats.MIN_CLASS_REVIEWS, mantap=20)

        self.assertIsNone(stats.homepage_stats()["mantap_percent"])

    def test_a_handful_of_ratings_is_not_a_percentage(self):
        self._reviews(stats.MIN_CLASS_REVIEWS - 1, mantap=stats.MIN_CLASS_REVIEWS - 1)

        self.assertIsNone(stats.homepage_stats()["mantap_percent"])

    def test_every_machine_needs_a_video_before_the_page_says_so(self):
        Equipment.objects.create(name="Leg Press", video_link="https://youtu.be/abc")
        Equipment.objects.create(name="Chest Press", video_link="https://youtu.be/def")
        self.assertTrue(stats.homepage_stats()["equipment_all_have_video"])

        cache.clear()
        Equipment.objects.create(name="Rowing", video_link="https://www.instagram.com/reel/xyz/")
        result = stats.homepage_stats()
        # a link that is not a YouTube video has no player, so it does not count
        self.assertFalse(result["equipment_all_have_video"])
        self.assertEqual(result["equipment_total"], 3)

    def test_second_read_is_served_from_the_cache(self):
        stats.homepage_stats()

        with self.assertNumQueries(0):
            stats.homepage_stats()

    def test_a_failed_read_is_not_cached(self):
        with patch.object(stats, "_compute", side_effect=ProgrammingError("no table")):
            with self.assertLogs("homepage.stats", level="WARNING"):
                self.assertEqual(stats.homepage_stats(), {})

        self.assertIsNone(cache.get(stats.CACHE_KEY))
        self.assertIn("pemula_share", stats.homepage_stats())



class HomepagePageTest(FreshCacheMixin, TestCase):
    def test_hero_uses_the_live_share(self):
        for i in range(60):
            make_member(i, pemula=i < 45)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "<strong>3 dari 4</strong> member kami juga mulai dari nol.")

    def test_hero_falls_back_when_there_is_no_number(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Banyak member kami juga mulai dari nol.")

    def test_homepage_renders_when_the_numbers_cannot_be_read(self):
        with patch.object(stats, "_compute", side_effect=OperationalError("gone")):
            with self.assertLogs("homepage.stats", level="WARNING"):
                response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Banyak member kami juga mulai dari nol.")

    def test_whatsapp_links_are_built_from_the_one_number(self):
        body = self.client.get(reverse("home")).content.decode()

        self.assertNotIn("wa.me/+", body)
        self.assertIn(f"https://wa.me/{business.WHATSAPP_NUMBER}", body)

    def test_programs_do_not_ask_for_the_price(self):
        response = self.client.get(reverse("home"))

        self.assertNotContains(response, "Tanya harga")
        self.assertNotContains(response, "tanya harga")
        for program in response.context["programs"]:
            self.assertNotIn("ask_url", program)

    def test_only_the_important_whatsapp_buttons(self):
        body = self.client.get(reverse("home")).content.decode()

        # hero, closing section, floating pill, plus the FAQ text link and the
        # footer number. The side menu has none.
        self.assertEqual(body.count(f"https://wa.me/{business.WHATSAPP_NUMBER}"), 5)
        self.assertNotIn("Tanya-tanya gratis</span>", body)

    def test_the_price_answer_sends_first_timers_to_the_gym(self):
        response = self.client.get(reverse("home"))

        answer = next(f["answer"] for f in response.context["faqs"] if f["question"] == "Berapa harganya?")
        self.assertIn("mampir", answer)
        self.assertIn("sudah biasa nge-gym", answer)

    def test_both_coaches_are_introduced_with_their_credentials(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Dastin N. Alfiyyah")
        self.assertContains(response, "Sertifikasi Advanced Fitness Trainer, Rai Institute")
        self.assertContains(response, "Naufal Fauzan")
        self.assertContains(response, "70 klien dalam 3 tahun terakhir")
        self.assertContains(response, "Coach Dastin</span>")
        self.assertContains(response, "Coach Naufal</span>")

    def test_the_top_numbers_leave_out_the_class_size(self):
        Class.objects.create(name="Kelas Pemula (Push)", max_members=6).schedules.create(
            day_of_week=0, start_time=time(7, 15), end_time=time(8, 15)
        )

        body = self.client.get(reverse("home")).content.decode()
        strip = body[body.index('class="hp-proof"'):body.index('id="kenapa"')]

        self.assertNotIn("Maks", strip)
        self.assertNotIn("Kelas maks", body[:body.index('class="hp-proof"')])
        # still said where it belongs, on the Kelas Pemula card
        self.assertContains(self.client.get(reverse("home")), "Latihan bareng maks 6 orang")

    def test_semi_private_is_sold_on_monthly_not_per_session(self):
        response = self.client.get(reverse("home"))

        semi = next(p for p in response.context["programs"] if p["key"] == "semi")
        self.assertIn("Bayar bulanan, bukan per sesi", semi["points"])
        self.assertIn("1-on-1", semi["text"])
        featured = [p["key"] for p in response.context["programs"] if p["featured"]]
        self.assertEqual(featured, ["pemula"])

    def test_visitor_sees_daftar_and_masuk(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Daftar member")
        self.assertContains(response, "Sudah member?")
        self.assertNotContains(response, "Akun Saya</a>")

    def test_member_sees_their_account_instead(self):
        member = make_member(1)
        session = self.client.session
        session["member_email"] = member.email
        session.save()

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Akun Saya</a>")
        self.assertNotContains(response, "Sudah member?")
        self.assertNotContains(response, "Daftar member")

    def test_query_count_is_pinned_once_the_numbers_are_cached(self):
        self.client.get(reverse("home"))

        # review summary + testimonials; the numbers come from the cache
        with self.assertNumQueries(2):
            self.client.get(reverse("home"))



class HomepageHasNoPricesTest(FreshCacheMixin, TestCase):
    """A first-timer hears the price in person, so it is never printed here."""

    def test_no_price_anywhere_on_the_page(self):
        body = self.client.get(reverse("home")).content.decode()

        self.assertNotRegex(body, r"Rp\s?\d")
        self.assertNotRegex(body, r"\d+\s?(ribu|rb)\b")

    def test_no_price_in_the_faq_or_structured_data(self):
        response = self.client.get(reverse("home"))

        text = json.dumps(response.context["faqs"]) + "".join(response.context["structured_data"])
        self.assertNotRegex(text, r"Rp\s?\d|\d+\s?(ribu|rb)\b|\"price\"")


class HomepageSeoTest(FreshCacheMixin, TestCase):
    def _get(self, **extra):
        response = self.client.get(reverse("home"), **extra)
        self.assertEqual(response.status_code, 200)
        return response, response.content.decode()

    def _ld_blocks(self, body):
        found = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
        return [json.loads(block) for block in found]

    def test_title_and_description_say_what_the_gym_is(self):
        _, body = self._get()

        self.assertIn(f"<title>{escape(content.SEO_TITLE)}</title>", body)
        self.assertIn("Gym Pemula", content.SEO_TITLE)
        description = re.search(r'<meta name="description" content="([^"]+)"', body).group(1)
        self.assertIn("Bandung", description)

    def test_description_fits_in_a_search_result_with_or_without_the_class_size(self):
        # Google cuts a description off at roughly 160 characters
        for known in ({}, {"pemula_class_size": 6}, {"pemula_class_size": 12}):
            self.assertLessEqual(len(content.seo_description(known)), 160, known)

    def test_structured_data_describes_the_gym(self):
        _, body = self._get()

        gym = next(b for b in self._ld_blocks(body) if b["@type"] == "ExerciseGym")
        self.assertEqual(gym["telephone"], business.PHONE_INTERNATIONAL)
        self.assertEqual(gym["address"]["postalCode"], business.POSTAL_CODE)
        self.assertEqual(gym["geo"]["latitude"], business.LATITUDE)
        self.assertNotIn("aggregateRating", gym)
        days = {spec["dayOfWeek"]: spec for spec in gym["openingHoursSpecification"]}
        self.assertEqual(len(days), 7)
        self.assertEqual(days["Sunday"]["opens"], "07:30")
        self.assertEqual(days["Monday"]["closes"], "21:00")

    def test_faq_structured_data_matches_the_visible_faq(self):
        response, body = self._get()

        faq = next(b for b in self._ld_blocks(body) if b["@type"] == "FAQPage")
        in_data = [q["name"] for q in faq["mainEntity"]]
        on_page = [item["question"] for item in response.context["faqs"]]
        self.assertEqual(in_data, on_page)
        for question in on_page:
            self.assertContains(response, f"<summary>{question}<i")

    def test_the_faq_keeps_the_landmark_capitals(self):
        response, body = self._get()

        self.assertIn("seberang SMPK 5 BPK Penabur", response.context["faqs"][-1]["answer"])
        self.assertNotIn("smpk", body)

    def test_a_missing_image_drops_out_of_the_structured_data(self):
        with patch("homepage.seo.static", side_effect=ValueError("not in manifest")):
            with self.assertLogs("homepage.seo", level="ERROR"):
                _, body = self._get()

        gym = next(b for b in self._ld_blocks(body) if b["@type"] == "ExerciseGym")
        self.assertEqual(gym["image"], [])

    def test_structured_data_cannot_close_its_own_script_tag(self):
        text = content.as_ld_json({"name": "</script><script>alert(1)</script>"})

        self.assertNotIn("<", text)
        self.assertEqual(json.loads(text)["name"], "</script><script>alert(1)</script>")


class HomepageStaticPathsTest(FreshCacheMixin, TestCase):
    """A static path missing from the manifest is a 500 in production, not a broken image."""

    def test_every_static_file_the_homepage_references_exists(self):
        body = self.client.get(reverse("home")).content.decode()

        paths = set(re.findall(r'(?:src|href|poster|data-src)="%s([^"?]+)' % settings.STATIC_URL, body))
        self.assertTrue(any(p.endswith("hero-loop.mp4") for p in paths))
        for path in sorted(paths):
            self.assertIsNotNone(finders.find(path), f"missing static file: {path}")

    def test_structured_data_images_exist(self):
        for path in content.STRUCTURED_DATA_IMAGES + [content.LOGO_IMAGE]:
            self.assertIsNotNone(finders.find(path), f"missing static file: {path}")

    def test_the_css_background_poster_exists(self):
        css = open(finders.find("css/style.css")).read()

        for url in re.findall(r'url\("\.\./(images/home/[^"]+)"\)', css):
            self.assertIsNotNone(finders.find(url), f"missing static file: {url}")
