import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Member

from . import content
from .analytics import question_stats
from .models import ChapterProgress, QuizAnswer

User = get_user_model()


def a_member(email="gizi@example.com", phone="628560001111"):
    return Member.objects.create(
        name="Gizi Member",
        email=email,
        phone_number=phone,
        gender="M",
        age=28,
        height=170,
        weight=68,
        years_of_working_out="belum pernah",
        goals="Turun berat badan",
        know_mulai_gym_from="friends",
    )


class ContentIntegrityTest(TestCase):
    """The content is a hand-written Python file, so these are its guardrails."""

    def quizzes(self):
        for chapter in content.CHAPTERS:
            for block in chapter["blocks"]:
                if block["type"] == "quiz":
                    yield chapter, block

    def test_chapter_slugs_and_numbers_are_unique(self):
        slugs = [chapter["slug"] for chapter in content.CHAPTERS]
        numbers = [chapter["number"] for chapter in content.CHAPTERS]

        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(len(numbers), len(set(numbers)))

    def test_question_keys_are_unique_across_every_chapter(self):
        # A key is stored on every recorded answer, so a duplicate would merge
        # two different questions' history.
        keys = [block["key"] for _, block in self.quizzes()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_answer_points_at_a_real_choice(self):
        for chapter, block in self.quizzes():
            choices = [choice["key"] for choice in block["choices"]]
            self.assertIn(
                block["answer"],
                choices,
                f"{block['key']} in {chapter['slug']} answers a choice that is not there",
            )

    def test_every_question_has_an_explanation_and_at_least_two_choices(self):
        for _, block in self.quizzes():
            self.assertTrue(block["explanation"].strip(), block["key"])
            self.assertGreaterEqual(len(block["choices"]), 2, block["key"])

    def test_every_verdict_row_has_a_claim_and_a_reason(self):
        rows = [
            row
            for chapter in content.CHAPTERS
            for block in chapter["blocks"]
            if block["type"] == "verdicts"
            for row in block["rows"]
        ]
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["claim"].strip())
            self.assertTrue(row["note"].strip())
            self.assertIsInstance(row["is_true"], bool)

    def test_every_chapter_has_an_emoji_and_a_title(self):
        for chapter in content.CHAPTERS:
            self.assertTrue(chapter["emoji"], chapter["slug"])
            self.assertTrue(chapter["title"], chapter["slug"])
            self.assertTrue(chapter["subtitle"], chapter["slug"])

    def test_every_block_type_has_a_template(self):
        from .views import BLOCK_TEMPLATES

        for chapter in content.CHAPTERS:
            for block in chapter["blocks"]:
                self.assertIn(block["type"], BLOCK_TEMPLATES, chapter["slug"])

    def test_every_chapter_has_questions_and_a_reading_time(self):
        for chapter in content.chapters():
            self.assertGreater(chapter["quiz_count"], 0, chapter["slug"])
            self.assertGreater(chapter["minutes"], 0, chapter["slug"])

    def test_the_level_bands_are_ordered_and_start_at_zero(self):
        mins = [level["min"] for level in content.LEVELS]

        self.assertEqual(mins[0], 0)
        self.assertEqual(mins, sorted(mins))
        self.assertEqual(len(mins), len(set(mins)))
        # The top band is only reachable by finishing everything.
        self.assertEqual(mins[-1], content.total_chapters())

    def test_every_level_chip_is_labelled(self):
        chips = content.level_chips()

        self.assertEqual(len(chips), len(content.LEVELS))
        for chip in chips:
            self.assertTrue(chip["label"].endswith("bab"))
            self.assertTrue(chip["name"])

    def test_there_is_a_level_name_for_every_number_of_finished_chapters(self):
        for done in range(content.total_chapters() + 1):
            self.assertTrue(content.level_name(done))

        # And beyond the list, so adding a chapter later cannot break it.
        self.assertEqual(
            content.level_name(content.total_chapters() + 5), content.LEVELS[-1]["name"]
        )


class MedalTest(TestCase):
    def test_all_correct_is_emas(self):
        self.assertEqual(content.medal(4, 4), "emas")

    def test_most_correct_is_perak(self):
        self.assertEqual(content.medal(3, 4), "perak")

    def test_finishing_badly_still_earns_perunggu(self):
        self.assertEqual(content.medal(1, 4), "perunggu")

    def test_no_questions_means_no_medal(self):
        self.assertIsNone(content.medal(0, 0))


class PagesTest(TestCase):
    def test_guest_can_read_the_index(self):
        response = self.client.get(reverse("nutrition:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belajar Gizi")
        for chapter in content.CHAPTERS:
            # escape(): "Gorengan & Minyak" reaches the page as "&amp;"
            self.assertContains(response, escape(chapter["title"]))

    def test_guest_is_told_progress_needs_signing_in(self):
        response = self.client.get(reverse("nutrition:index"))

        self.assertContains(response, reverse("member_login"))

    def test_guest_can_read_a_chapter(self):
        response = self.client.get(reverse("nutrition:chapter", args=["kalori"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kalori")

    def test_unknown_chapter_is_a_404(self):
        response = self.client.get(reverse("nutrition:chapter", args=["mie-ayam"]))

        self.assertEqual(response.status_code, 404)

    def test_member_sees_their_level(self):
        member = a_member()
        session = self.client.session
        session["member_email"] = member.email
        session.save()

        response = self.client.get(reverse("nutrition:index"))

        self.assertContains(response, content.LEVELS[0]["name"])

    def test_account_page_shows_the_teaser(self):
        member = a_member()
        session = self.client.session
        session["member_email"] = member.email
        session.save()

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "Belajar Gizi")
        self.assertEqual(
            response.context["gizi"]["total_chapters"], content.total_chapters()
        )


class FinishChapterTest(TestCase):
    def setUp(self):
        self.member = a_member()
        self.chapter = content.get_chapter("kalori")
        self.url = reverse("nutrition:finish", args=["kalori"])

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def all_right(self):
        return {
            block["key"]: block["answer"]
            for block in self.chapter["blocks"]
            if block["type"] == "quiz"
        }

    def post(self, answers):
        return self.client.post(
            self.url, data=json.dumps({"answers": answers}), content_type="application/json"
        )

    def test_a_perfect_run_is_saved_with_a_gold_medal(self):
        self.login()

        response = self.post(self.all_right())
        body = response.json()

        self.assertTrue(body["saved"])
        self.assertEqual(body["correct"], body["total"])
        self.assertEqual(body["medal"], "emas")
        self.assertEqual(body["finished_count"], 1)

        saved = ChapterProgress.objects.get(member=self.member, chapter_slug="kalori")
        self.assertEqual(saved.correct, saved.total)
        self.assertEqual(saved.attempts, 1)

    def test_every_answer_is_recorded(self):
        self.login()

        self.post(self.all_right())

        self.assertEqual(
            QuizAnswer.objects.filter(member=self.member).count(),
            self.chapter["quiz_count"],
        )
        self.assertTrue(all(a.is_correct for a in QuizAnswer.objects.all()))

    def test_the_score_comes_from_the_content_not_the_browser(self):
        self.login()
        answers = self.all_right()
        first_key = next(iter(answers))
        answers[first_key] = "z"  # a choice that does not exist

        body = self.post(answers).json()

        self.assertEqual(body["correct"], self.chapter["quiz_count"] - 1)
        self.assertFalse(
            QuizAnswer.objects.get(question_key=first_key).is_correct
        )

    def test_a_skipped_question_counts_as_wrong_and_records_no_choice(self):
        self.login()

        body = self.post({}).json()

        self.assertEqual(body["correct"], 0)
        self.assertEqual(body["total"], self.chapter["quiz_count"])
        self.assertTrue(all(a.chosen == "" for a in QuizAnswer.objects.all()))

    def test_a_retake_keeps_the_best_score(self):
        self.login()
        answers = self.all_right()
        first_key = next(iter(answers))

        self.post(answers)  # perfect
        answers[first_key] = "z"
        self.post(answers)  # worse

        saved = ChapterProgress.objects.get(member=self.member, chapter_slug="kalori")
        self.assertEqual(saved.attempts, 2)
        self.assertEqual(saved.best_correct, self.chapter["quiz_count"])
        self.assertEqual(saved.correct, self.chapter["quiz_count"] - 1)

    def test_a_retake_does_not_create_a_second_progress_row(self):
        self.login()

        self.post(self.all_right())
        self.post(self.all_right())

        self.assertEqual(ChapterProgress.objects.count(), 1)

    def test_a_guest_is_graded_but_nothing_is_stored(self):
        body = self.post(self.all_right()).json()

        self.assertFalse(body["saved"])
        self.assertEqual(body["correct"], self.chapter["quiz_count"])
        self.assertEqual(ChapterProgress.objects.count(), 0)
        self.assertEqual(QuizAnswer.objects.count(), 0)

    def test_finishing_every_chapter_reaches_the_top_level(self):
        self.login()
        for chapter in content.CHAPTERS:
            answers = {
                block["key"]: block["answer"]
                for block in chapter["blocks"]
                if block["type"] == "quiz"
            }
            body = self.client.post(
                reverse("nutrition:finish", args=[chapter["slug"]]),
                data=json.dumps({"answers": answers}),
                content_type="application/json",
            ).json()

        self.assertTrue(body["all_done"])
        self.assertEqual(body["level"], content.LEVELS[-1]["name"])

    def test_garbage_body_is_rejected_not_crashed(self):
        self.login()

        response = self.client.post(
            self.url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            self.url, data=json.dumps({"answers": "nope"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class AnalyticsTest(TestCase):
    """The admin page, and the one rule that makes its numbers honest."""

    def setUp(self):
        self.member = a_member()
        self.staff = User.objects.create_superuser(
            "gizi-admin", "gizi-admin@example.com", "password"
        )
        self.chapter = content.get_chapter("kalori")
        self.first_question = next(
            block for block in self.chapter["blocks"] if block["type"] == "quiz"
        )

    def answer(self, correct):
        QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key=self.first_question["key"],
            chosen=self.first_question["answer"] if correct else "z",
            is_correct=correct,
        )

    def stats_for_first_question(self):
        return next(
            row for row in question_stats() if row["key"] == self.first_question["key"]
        )

    def test_miss_rate_uses_the_first_answer_not_the_retake(self):
        self.answer(correct=False)
        self.answer(correct=True)  # read the explanation, tried again

        row = self.stats_for_first_question()

        self.assertEqual(row["answered"], 1)
        self.assertEqual(row["wrong"], 1)
        self.assertEqual(row["miss_percent"], 100)

    def test_a_question_nobody_answered_shows_zero_of_zero(self):
        row = self.stats_for_first_question()

        self.assertEqual(row["answered"], 0)
        self.assertEqual(row["miss_percent"], 0)

    def test_the_most_chosen_wrong_answer_is_named(self):
        other = a_member(email="two@example.com", phone="628560002222")
        wrong_choice = next(
            choice["key"]
            for choice in self.first_question["choices"]
            if choice["key"] != self.first_question["answer"]
        )
        for member in (self.member, other):
            QuizAnswer.objects.create(
                member=member,
                chapter_slug="kalori",
                question_key=self.first_question["key"],
                chosen=wrong_choice,
                is_correct=False,
            )

        row = self.stats_for_first_question()

        self.assertEqual(row["top_wrong_count"], 2)
        self.assertIn(row["top_wrong_text"], [c["text"] for c in self.first_question["choices"]])

    def test_staff_can_open_the_page(self):
        self.client.login(username="gizi-admin", password="password")

        response = self.client.get(reverse("admin:belajar-gizi"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yang paling sering salah")

    def test_a_visitor_cannot(self):
        response = self.client.get(reverse("admin:belajar-gizi"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
