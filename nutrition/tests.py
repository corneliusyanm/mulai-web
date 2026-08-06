import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import Member

from . import content, daily
from .analytics import question_stats
from .models import ChapterProgress, DailyAnswer, DailyQuestion, QuizAnswer
from .shuffle import place_answer

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


class AnswerPlacementTest(TestCase):
    """The correct answer must not sit in the same slot every time.

    Authored by hand, 77 of the 100 daily questions had the answer at B and none
    at C, so "always pick the middle one" scored 77% without reading a word. These
    are the guardrails against that coming back.
    """

    def daily_answers(self):
        from .daily_questions import QUESTIONS

        return [question["answer"] for question in QUESTIONS]

    def chapter_answers(self):
        return [
            block["answer"]
            for chapter in content.CHAPTERS
            for block in chapter["blocks"]
            if block["type"] == "quiz"
        ]

    def test_no_letter_dominates_the_daily_set(self):
        from .daily_questions import QUESTIONS

        # Grouped by how many choices a question has: the newer questions have
        # four, and mixing them into one tally would hide a lopsided group.
        groups = {}
        for question in QUESTIONS:
            size = len(question["choices"])
            groups.setdefault(size, []).append(question["answer"])

        for size, answers in groups.items():
            counts = {letter: answers.count(letter) for letter in "abcdefgh"[:size]}
            self.assertEqual(
                sum(counts.values()), len(answers), f"{size}-choice: unknown letter"
            )
            for letter, count in counts.items():
                # Every slot gets used, and none takes half, or a member can beat
                # the quiz by always picking the same letter.
                self.assertGreater(count, 0, f"{size}-choice: {letter} unused {counts}")
                self.assertLess(
                    count,
                    len(answers) / 2,
                    f"{size}-choice: {letter} dominates {counts}",
                )

    def test_no_letter_dominates_the_chapter_set(self):
        # Grouped by choice count, like the daily set: a lopsided four-choice
        # group would otherwise hide inside the three-choice tally.
        groups = {}
        for chapter in content.CHAPTERS:
            for block in chapter["blocks"]:
                if block["type"] == "quiz":
                    groups.setdefault(len(block["choices"]), []).append(block["answer"])

        for size, answers in groups.items():
            counts = {letter: answers.count(letter) for letter in "abcdefgh"[:size]}
            self.assertEqual(
                sum(counts.values()), len(answers), f"{size}-choice: unknown letter"
            )
            for letter, count in counts.items():
                self.assertLess(
                    count,
                    len(answers) / 2,
                    f"{size}-choice: {letter} dominates {counts}",
                )
            # Only meaningful once the group is big enough for every slot to have
            # had a fair chance of being picked.
            if len(answers) >= size * 2:
                for letter, count in counts.items():
                    self.assertGreater(
                        count, 0, f"{size}-choice: {letter} unused {counts}"
                    )

    def test_the_newest_chapter_asks_harder_questions(self):
        """New chapters get four choices, so the bar does not slip back.

        The early chapters ask things you can answer in five seconds. From chapter
        10 on the questions are meant to make somebody think, and four choices is
        the floor of that: a blind guess drops from 33% to 25%.
        """
        newest = max(content.CHAPTERS, key=lambda chapter: chapter["number"])

        quizzes = [b for b in newest["blocks"] if b["type"] == "quiz"]
        self.assertTrue(quizzes, newest["slug"])
        for block in quizzes:
            self.assertGreaterEqual(
                len(block["choices"]), 4, f"{block['key']} in {newest['slug']}"
            )
            # An explanation that only restates the answer teaches nothing.
            self.assertGreater(len(block["explanation"]), 120, block["key"])

    def test_placement_is_stable_for_the_same_code(self):
        choices = [{"key": "a", "text": "satu"}, {"key": "b", "text": "dua"}]

        first = place_answer("dq-001", choices, "a")
        second = place_answer("dq-001", choices, "a")

        self.assertEqual(first, second)

    def test_placement_moves_the_answer_without_losing_a_choice(self):
        choices = [
            {"key": "a", "text": "satu"},
            {"key": "b", "text": "dua"},
            {"key": "c", "text": "tiga"},
        ]

        placed, answer = place_answer("dq-042", choices, "b")

        self.assertEqual([c["key"] for c in placed], ["a", "b", "c"])
        self.assertEqual(
            sorted(c["text"] for c in placed), ["dua", "satu", "tiga"]
        )
        # Whichever slot it landed in, it still points at the same text.
        moved = next(c for c in placed if c["key"] == answer)
        self.assertEqual(moved["text"], "dua")

    def test_an_answer_naming_no_choice_is_left_alone(self):
        choices = [{"key": "a", "text": "satu"}]

        placed, answer = place_answer("dq-001", choices, "z")

        self.assertEqual(placed, choices)
        self.assertEqual(answer, "z")


class DailyRotationTest(TestCase):
    def test_the_same_day_gives_the_same_question_to_everyone(self):
        day = daily.ROTATION_EPOCH + timedelta(days=5)

        self.assertEqual(daily.question_for(day), daily.question_for(day))

    def test_consecutive_days_give_different_questions(self):
        first = daily.question_for(daily.ROTATION_EPOCH)
        second = daily.question_for(daily.ROTATION_EPOCH + timedelta(days=1))

        self.assertNotEqual(first.code, second.code)

    def test_the_rotation_wraps_after_the_last_question(self):
        total = DailyQuestion.rotation().count()

        first = daily.question_for(daily.ROTATION_EPOCH)
        wrapped = daily.question_for(daily.ROTATION_EPOCH + timedelta(days=total))

        self.assertEqual(first.code, wrapped.code)

    def test_dates_before_the_epoch_still_get_a_question(self):
        self.assertIsNotNone(daily.question_for(daily.ROTATION_EPOCH - timedelta(days=3)))

    def test_deactivated_questions_drop_out_of_the_rotation(self):
        question = daily.question_for(daily.ROTATION_EPOCH)
        question.is_active = False
        question.save()

        self.assertNotEqual(
            daily.question_for(daily.ROTATION_EPOCH).code, question.code
        )

    def test_no_active_questions_means_no_state_rather_than_a_crash(self):
        DailyQuestion.objects.update(is_active=False)

        self.assertIsNone(daily.question_for())
        self.assertIsNone(daily.state_for(None))


class DailyAnswerTest(TestCase):
    def setUp(self):
        self.member = a_member()
        self.today = timezone.localdate()
        self.question = daily.question_for(self.today)

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def answer(self, choice):
        return self.client.post(reverse("nutrition:daily_answer"), {"choice": choice})

    def test_answering_correctly_is_recorded(self):
        self.login()

        self.answer(self.question.answer)

        saved = DailyAnswer.objects.get()
        self.assertEqual(saved.member, self.member)
        self.assertEqual(saved.answer_date, self.today)
        self.assertTrue(saved.is_correct)

    def test_grading_happens_on_the_server(self):
        self.login()
        wrong = next(
            c["key"] for c in self.question.choices if c["key"] != self.question.answer
        )

        self.answer(wrong)

        self.assertFalse(DailyAnswer.objects.get().is_correct)

    def test_only_one_shot_a_day(self):
        self.login()
        wrong = next(
            c["key"] for c in self.question.choices if c["key"] != self.question.answer
        )

        self.answer(wrong)
        self.answer(self.question.answer)  # trying again

        saved = DailyAnswer.objects.get()
        self.assertEqual(DailyAnswer.objects.count(), 1)
        self.assertFalse(saved.is_correct)
        self.assertEqual(saved.chosen, wrong)

    def test_a_second_day_is_a_new_shot(self):
        daily.record(self.member, self.today - timedelta(days=1), self.question, "a")
        self.login()

        self.answer(self.question.answer)

        self.assertEqual(DailyAnswer.objects.count(), 2)

    def test_a_guest_is_graded_but_not_stored(self):
        response = self.answer(self.question.answer)

        self.assertEqual(DailyAnswer.objects.count(), 0)
        # Kept in the session so the explanation survives the redirect.
        self.assertEqual(
            self.client.session["daily_answer"]["date"], self.today.isoformat()
        )
        self.assertTrue(self.client.session["daily_answer"]["is_correct"])
        self.assertEqual(response.status_code, 302)

    def test_the_fetch_path_gets_json_with_the_explanation(self):
        self.login()

        response = self.client.post(
            reverse("nutrition:daily_answer"),
            {"choice": self.question.answer},
            headers={"X-Gizi-Fetch": "1"},
        )
        body = response.json()

        self.assertTrue(body["saved"])
        self.assertTrue(body["correct"])
        self.assertEqual(body["answer"], self.question.answer)
        self.assertEqual(body["explanation"], self.question.explanation)

    def test_get_is_not_allowed(self):
        self.assertEqual(
            self.client.get(reverse("nutrition:daily_answer")).status_code, 405
        )


class DailyStreakTest(TestCase):
    def setUp(self):
        self.member = a_member()
        self.today = timezone.localdate()
        self.question = daily.question_for(self.today)

    def answered_on(self, *offsets):
        for offset in offsets:
            day = self.today - timedelta(days=offset)
            DailyAnswer.objects.create(
                member=self.member,
                question=self.question,
                answer_date=day,
                chosen="a",
                is_correct=True,
            )

    def test_no_answers_is_no_streak(self):
        self.assertEqual(daily.streak(self.member, self.today), 0)

    def test_three_days_in_a_row_counting_today(self):
        self.answered_on(0, 1, 2)

        self.assertEqual(daily.streak(self.member, self.today), 3)

    def test_today_being_unanswered_does_not_break_it_yet(self):
        # Otherwise every member sees a zero every morning.
        self.answered_on(1, 2, 3)

        self.assertEqual(daily.streak(self.member, self.today), 3)

    def test_a_missed_day_resets_it(self):
        self.answered_on(0, 1, 3, 4)

        self.assertEqual(daily.streak(self.member, self.today), 2)

    def test_a_wrong_answer_still_keeps_the_streak(self):
        # Showing up is the habit; being right is the leaderboard's business.
        DailyAnswer.objects.create(
            member=self.member,
            question=self.question,
            answer_date=self.today,
            chosen="z",
            is_correct=False,
        )

        self.assertEqual(daily.streak(self.member, self.today), 1)

    def test_a_guest_has_no_streak(self):
        self.assertEqual(daily.streak(None, self.today), 0)


class DailySplitTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.question = daily.question_for(self.today)

    def answers(self, chosen, count, correct=False):
        for index in range(count):
            member = a_member(f"split{chosen}{index}@example.com", f"62857100{chosen}{index:03}")
            DailyAnswer.objects.create(
                member=member,
                question=self.question,
                answer_date=self.today - timedelta(days=index),
                chosen=chosen,
                is_correct=correct,
            )

    def test_too_few_answers_shows_nothing(self):
        self.answers("a", 3)

        self.assertEqual(daily.choice_split(self.question), {})

    def test_percentages_once_there_is_a_sample(self):
        self.answers("a", 6)
        self.answers("b", 2)

        split = daily.choice_split(self.question)

        self.assertEqual(split["a"], 75)
        self.assertEqual(split["b"], 25)

    def test_blank_answers_are_not_counted(self):
        self.answers("a", 6)
        DailyAnswer.objects.create(
            member=a_member("blank@example.com", "628571999999"),
            question=self.question,
            answer_date=self.today,
            chosen="",
            is_correct=False,
        )

        self.assertEqual(daily.choice_split(self.question)["a"], 100)


class DailyPageTest(TestCase):
    def setUp(self):
        self.member = a_member()
        self.today = timezone.localdate()
        self.question = daily.question_for(self.today)

    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_a_guest_can_read_todays_question(self):
        response = self.client.get(reverse("nutrition:daily"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, escape(self.question.question))
        self.assertFalse(response.context["daily"]["answered"])

    def test_the_page_does_not_give_the_answer_away_before_answering(self):
        response = self.client.get(reverse("nutrition:daily"))
        body = response.content.decode()

        # No choice is marked, and unlike the chapter quiz the correct key is not
        # in the markup at all: there is a leaderboard point on this one.
        self.assertNotIn("gizi-choice is-correct", body)
        self.assertNotIn('data-answer="', body)
        self.assertNotContains(response, escape(self.question.explanation))

    def test_after_answering_the_explanation_is_there(self):
        self.login()
        daily.record(self.member, self.today, self.question, self.question.answer)

        response = self.client.get(reverse("nutrition:daily"))

        self.assertTrue(response.context["daily"]["answered"])
        self.assertContains(response, escape(self.question.explanation))

    def test_the_teaser_appears_on_the_account_page(self):
        self.login()

        response = self.client.get(reverse("member_details"))

        self.assertContains(response, "Kuis Harian")
        self.assertEqual(response.context["daily"]["question"], self.question)

    def test_the_teaser_appears_on_the_belajar_gizi_index(self):
        response = self.client.get(reverse("nutrition:index"))

        self.assertContains(response, "Kuis Harian")


class DailyQuestionSeedTest(TestCase):
    def test_the_migration_seeded_every_question(self):
        from .daily_questions import QUESTIONS

        self.assertEqual(DailyQuestion.objects.count(), len(QUESTIONS))

    def test_codes_are_unique_and_positions_run_in_order(self):
        codes = list(DailyQuestion.objects.values_list("code", flat=True))
        positions = sorted(DailyQuestion.objects.values_list("position", flat=True))

        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(positions, list(range(1, len(positions) + 1)))

    def test_every_seeded_answer_names_a_real_choice(self):
        for question in DailyQuestion.objects.all():
            keys = [choice["key"] for choice in question.choices]
            self.assertIn(question.answer, keys, question.code)

    def test_syncing_again_adds_nothing(self):
        from .daily_questions import QUESTIONS

        added = daily.sync_questions(DailyQuestion, QUESTIONS)

        self.assertEqual(added, 0)

    def test_a_new_question_gets_the_next_position(self):
        # Derived, not hard-coded: this used to say 101 and broke the first time
        # a batch was appended.
        seeded = DailyQuestion.objects.count()

        question = DailyQuestion.objects.create(
            code="dq-999",
            question="Soal baru",
            choices=[{"key": "a", "text": "ya"}, {"key": "b", "text": "nggak"}],
            answer="a",
            explanation="Karena begitu.",
        )

        self.assertEqual(question.position, seeded + 1)


class DailyDifficultyTest(TestCase):
    """From dq-101 on, the questions are meant to make somebody think.

    The first hundred were answerable in five seconds, which is fine but does not
    teach much. These pin the shape of the newer ones so the bar does not quietly
    slip back.
    """

    def newer_questions(self):
        from .daily_questions import QUESTIONS

        return [q for q in QUESTIONS if q["position"] > 100]

    def test_the_newer_questions_have_four_choices(self):
        # Four choices drops a blind guess from 33% to 25%.
        for question in self.newer_questions():
            self.assertEqual(len(question["choices"]), 4, question["code"])

    def test_every_choice_has_text_and_a_unique_key(self):
        from .daily_questions import QUESTIONS

        for question in QUESTIONS:
            keys = [choice["key"] for choice in question["choices"]]
            self.assertEqual(len(keys), len(set(keys)), question["code"])
            for choice in question["choices"]:
                self.assertTrue(choice["text"].strip(), question["code"])

    def test_the_newer_explanations_actually_explain(self):
        # A one-liner that restates the answer teaches nothing, so hold these to
        # a length that forces a reason.
        for question in self.newer_questions():
            self.assertGreater(
                len(question["explanation"]), 80, question["code"]
            )

    def test_there_are_ageing_questions_now(self):
        from .daily_questions import QUESTIONS

        haystack = " ".join(q["question"] + q["explanation"] for q in QUESTIONS).lower()

        for word in ("umur 70", "otot", "tulang", "mandiri"):
            self.assertIn(word, haystack)
