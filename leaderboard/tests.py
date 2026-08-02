"""The leaderboard: points, ranks, periods, and who can see it.

Needs Postgres: the board is one raw statement using DISTINCT ON and AT TIME ZONE.
"""

from datetime import date, time, timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Member
from classes.models import Class, ClassInstance, ClassMiss, ClassSchedule
from nutrition.models import DailyAnswer, DailyQuestion, QuizAnswer
from visits.models import Visit

from . import board as B


class BoardTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.today = timezone.localdate()
        self.this_month = B.month_period(self.today.year, self.today.month)
        self.lifetime = B.lifetime_period()
        self.member = self.a_member("board@example.com", "628580000001", "Cornelius Yan Mintareja")

    def tearDown(self):
        cache.clear()

    def a_member(self, email, phone, name="Board Member"):
        return Member.objects.create(
            name=name,
            email=email,
            phone_number=phone,
            gender="M",
            age=30,
            height=170,
            weight=70,
            years_of_working_out="1 tahun",
            goals="Stay fit",
            know_mulai_gym_from="friends",
            active_until=timezone.now() + timedelta(days=30),
            pemula_active_until=timezone.now() + timedelta(days=30),
        )

    def visit_on(self, day, member=None, hour=8):
        visit = Visit.objects.create(member=member or self.member)
        when = timezone.make_aware(timezone.datetime.combine(day, time(hour, 30)))
        Visit.objects.filter(pk=visit.pk).update(check_in_time=when)
        return visit

    def class_on(self, day, hour=7):
        klass, _ = Class.objects.get_or_create(
            name="Kelas Pemula", defaults={"description": "Beginner", "max_members": 10}
        )
        schedule, _ = ClassSchedule.objects.get_or_create(
            class_obj=klass,
            day_of_week=day.weekday(),
            start_time=time(hour, 0),
            defaults={"end_time": time(hour + 1, 0)},
        )
        return ClassInstance.objects.create(
            class_schedule=schedule,
            date=day,
            start_time=time(hour, 0),
            end_time=time(hour + 1, 0),
        )

    def row_for(self, period, member=None):
        member = member or self.member
        rows = B.compute(period)
        return next((r for r in rows if r["member_id"] == member.id), None)


class DisplayNameTest(TestCase):
    def test_first_name_stays_whole_and_the_rest_become_initials(self):
        self.assertEqual(
            B.display_name("Cornelius Yan Mintareja"), "Cornelius Y. M."
        )

    def test_a_single_name_is_left_alone(self):
        self.assertEqual(B.display_name("Nana"), "Nana")

    def test_extra_spaces_do_not_produce_empty_initials(self):
        self.assertEqual(B.display_name("  Dila  Rahma Putri "), "Dila R. P.")

    def test_a_non_latin_name_survives(self):
        self.assertEqual(B.display_name("郑美珍"), "郑美珍")

    def test_an_empty_name_gets_a_placeholder(self):
        self.assertEqual(B.display_name(""), "Member")
        self.assertEqual(B.display_name(None), "Member")


class PeriodTest(TestCase):
    def test_months_start_at_the_earliest_month(self):
        months = B.months_available(date(2026, 10, 15))
        keys = [month["key"] for month in months]

        self.assertEqual(keys, ["2026-10", "2026-09", "2026-08"])

    def test_the_current_month_is_first(self):
        months = B.months_available(date(2026, 9, 2))

        self.assertEqual(months[0]["key"], "2026-09")

    def test_a_month_period_covers_the_whole_month(self):
        period = B.month_period(2026, 8)

        self.assertEqual(period["start"], date(2026, 8, 1))
        self.assertEqual(period["end"], date(2026, 8, 31))

    def test_december_rolls_into_january(self):
        period = B.month_period(2026, 12)

        self.assertEqual(period["end"], date(2026, 12, 31))

    def test_lifetime_has_no_bounds(self):
        period = B.lifetime_period()

        self.assertIsNone(period["start"])
        self.assertIsNone(period["end"])

    def test_garbage_falls_back_to_this_month(self):
        today = timezone.localdate()

        for value in ("wat", "", None, "2026", "abc-def", "2026-13"):
            self.assertEqual(
                B.resolve_period(value, today)["key"],
                f"{today.year:04d}-{today.month:02d}",
                value,
            )

    def test_months_before_the_board_existed_fall_back(self):
        self.assertEqual(
            B.resolve_period("2026-06", date(2026, 9, 1))["key"], "2026-09"
        )

    def test_a_month_in_the_future_falls_back(self):
        self.assertEqual(
            B.resolve_period("2027-01", date(2026, 9, 1))["key"], "2026-09"
        )

    def test_a_real_past_month_resolves(self):
        self.assertEqual(
            B.resolve_period("2026-08", date(2026, 9, 1))["key"], "2026-08"
        )


class PointsTest(BoardTestCase):
    def test_a_visit_is_worth_eight(self):
        self.visit_on(self.today)

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["visits"], 1)
        self.assertEqual(row["total"], B.POINTS["visits"])

    def test_a_class_attended_pays_on_top_of_the_visit(self):
        instance = self.class_on(self.today)
        instance.booked_members.add(self.member)
        self.visit_on(self.today)

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["classes"], 1)
        self.assertEqual(row["total"], B.POINTS["visits"] + B.POINTS["classes"])

    def test_a_class_booked_but_not_attended_pays_nothing(self):
        instance = self.class_on(self.today - timedelta(days=1))
        instance.booked_members.add(self.member)

        row = self.row_for(self.this_month)

        self.assertIsNone(row)

    def test_a_cancelled_class_never_counts(self):
        instance = self.class_on(self.today)
        instance.booked_members.add(self.member)
        instance.status = "CANCELLED"
        instance.save()
        self.visit_on(self.today)

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["classes"], 0)

    def test_a_correct_gizi_answer_is_worth_two(self):
        QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key="kalori-1",
            chosen="a",
            is_correct=True,
        )

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["gizi"], 1)
        self.assertEqual(row["total"], B.POINTS["gizi"])

    def test_a_wrong_gizi_answer_is_worth_nothing(self):
        QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key="kalori-1",
            chosen="z",
            is_correct=False,
        )

        self.assertIsNone(self.row_for(self.this_month))

    def test_retaking_a_chapter_cannot_farm_points(self):
        # Wrong first, right on the retake. Only the first answer counts, so this
        # question pays nothing, ever.
        QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key="kalori-1",
            chosen="z",
            is_correct=False,
        )
        QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key="kalori-1",
            chosen="a",
            is_correct=True,
        )

        self.assertIsNone(self.row_for(self.this_month))

    def test_a_second_correct_answer_to_the_same_question_pays_once(self):
        for _ in range(3):
            QuizAnswer.objects.create(
                member=self.member,
                chapter_slug="kalori",
                question_key="kalori-1",
                chosen="a",
                is_correct=True,
            )

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["gizi"], 1)

    def test_a_correct_daily_answer_is_worth_one(self):
        question = DailyQuestion.objects.create(
            code="dq-test",
            question="Soal",
            choices=[{"key": "a", "text": "ya"}],
            answer="a",
            explanation="Karena.",
        )
        DailyAnswer.objects.create(
            member=self.member,
            question=question,
            answer_date=self.today,
            chosen="a",
            is_correct=True,
        )

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["daily"], 1)
        self.assertEqual(row["total"], B.POINTS["daily"])

    def test_a_missed_day_costs_ten(self):
        instance = self.class_on(self.today - timedelta(days=1))
        ClassMiss.objects.create(
            member=self.member,
            class_instance=instance,
            class_date=instance.date,
            class_name="Kelas Pemula",
        )
        self.visit_on(self.today)

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["misses"], 1)
        self.assertEqual(row["total"], B.POINTS["visits"] + B.POINTS["misses"])

    def test_two_classes_missed_on_one_day_cost_ten_not_twenty(self):
        # Same rule as the penalty: a strike is a day, not a class.
        day = self.today - timedelta(days=1)
        for hour in (7, 18):
            instance = self.class_on(day, hour=hour)
            ClassMiss.objects.create(
                member=self.member,
                class_instance=instance,
                class_date=day,
                class_name="Kelas Pemula",
            )

        row = self.row_for(self.this_month)

        self.assertEqual(row["counts"]["misses"], 1)
        self.assertEqual(row["total"], B.POINTS["misses"])

    def test_points_can_go_negative(self):
        instance = self.class_on(self.today - timedelta(days=1))
        ClassMiss.objects.create(
            member=self.member,
            class_instance=instance,
            class_date=instance.date,
            class_name="Kelas Pemula",
        )

        row = self.row_for(self.this_month)

        self.assertEqual(row["total"], B.POINTS["misses"])


class PeriodFilteringTest(BoardTestCase):
    def test_last_months_visit_is_out_of_this_months_board(self):
        last_month = (self.today.replace(day=1) - timedelta(days=1))
        self.visit_on(last_month)

        self.assertIsNone(self.row_for(self.this_month))
        self.assertEqual(self.row_for(self.lifetime)["counts"]["visits"], 1)

    def test_lifetime_adds_the_months_up(self):
        last_month = self.today.replace(day=1) - timedelta(days=1)
        self.visit_on(last_month)
        self.visit_on(self.today)

        self.assertEqual(self.row_for(self.lifetime)["counts"]["visits"], 2)
        self.assertEqual(self.row_for(self.this_month)["counts"]["visits"], 1)

    def test_a_gizi_answer_scores_in_the_month_it_was_first_given(self):
        answer = QuizAnswer.objects.create(
            member=self.member,
            chapter_slug="kalori",
            question_key="kalori-1",
            chosen="a",
            is_correct=True,
        )
        last_month = self.today.replace(day=1) - timedelta(days=1)
        QuizAnswer.objects.filter(pk=answer.pk).update(
            created_at=timezone.make_aware(
                timezone.datetime.combine(last_month, time(10, 0))
            )
        )

        self.assertIsNone(self.row_for(self.this_month))
        self.assertEqual(self.row_for(self.lifetime)["counts"]["gizi"], 1)


class RankingTest(BoardTestCase):
    def test_higher_points_rank_first(self):
        other = self.a_member("second@example.com", "628580000002", "Second Member")
        self.visit_on(self.today)
        self.visit_on(self.today, member=other)
        self.visit_on(self.today - timedelta(days=1), member=other)

        rows = B.compute(self.this_month)

        self.assertEqual(rows[0]["member_id"], other.id)
        self.assertEqual(rows[0]["rank"], 1)
        self.assertEqual(rows[1]["rank"], 2)

    def test_a_tie_shares_a_rank_and_the_next_one_skips(self):
        second = self.a_member("tie1@example.com", "628580000003", "Tie One")
        third = self.a_member("tie2@example.com", "628580000004", "Tie Two")
        lower = self.a_member("low@example.com", "628580000005", "Low Member")
        for member in (second, third):
            self.visit_on(self.today, member=member)
            self.visit_on(self.today - timedelta(days=1), member=member)
        self.visit_on(self.today, member=lower)

        rows = B.compute(self.this_month)
        ranks = [row["rank"] for row in rows]

        self.assertEqual(ranks, [1, 1, 3])

    def test_members_with_no_activity_are_left_out(self):
        self.a_member("quiet@example.com", "628580000006", "Quiet Member")
        self.visit_on(self.today)

        rows = B.compute(self.this_month)

        self.assertEqual(len(rows), 1)

    def test_names_are_shortened_on_the_board(self):
        self.visit_on(self.today)

        self.assertEqual(B.compute(self.this_month)[0]["name"], "Cornelius Y. M.")


class BoardAssemblyTest(BoardTestCase):
    def test_the_podium_takes_the_first_three(self):
        for index in range(5):
            member = self.a_member(f"p{index}@example.com", f"62858100{index:04}", f"P{index} X")
            for _ in range(index + 1):
                self.visit_on(self.today, member=member)

        data = B.board(self.this_month, member=self.member)

        self.assertEqual(len(data["podium"]), 3)
        self.assertEqual([row["rank"] for row in data["podium"]], [1, 2, 3])
        self.assertEqual(data["rest"][0]["rank"], 4)

    def test_the_top_is_capped(self):
        for index in range(6):
            member = self.a_member(f"c{index}@example.com", f"62858200{index:04}", f"C{index} X")
            self.visit_on(self.today, member=member)

        data = B.board(self.this_month, top=4, member=self.member)

        self.assertEqual(len(data["rows"]), 4)
        self.assertEqual(data["total_members"], 6)

    def test_a_member_with_no_points_still_gets_their_own_row(self):
        data = B.board(self.this_month, member=self.member)

        self.assertEqual(data["mine"]["total"], 0)
        self.assertIsNone(data["mine"]["rank"])
        self.assertFalse(data["mine_in_top"])

    def test_a_member_in_the_top_is_flagged(self):
        self.visit_on(self.today)

        data = B.board(self.this_month, member=self.member)

        self.assertTrue(data["mine_in_top"])
        self.assertEqual(data["mine"]["total"], B.POINTS["visits"])

    def test_a_guest_gets_no_own_row(self):
        self.assertIsNone(B.board(self.this_month)["mine"])

    def test_the_second_call_comes_from_cache(self):
        self.visit_on(self.today)
        B.board(self.this_month, member=self.member)

        with self.assertNumQueries(0):
            B.board(self.this_month, member=self.member)

    def test_each_period_is_cached_separately(self):
        self.visit_on(self.today)

        month = B.board(self.this_month, member=self.member)
        lifetime = B.board(self.lifetime, member=self.member)

        self.assertEqual(month["period"]["key"], self.this_month["key"])
        self.assertEqual(lifetime["period"]["key"], "lifetime")


class BoardViewTest(BoardTestCase):
    def login(self):
        session = self.client.session
        session["member_email"] = self.member.email
        session.save()

    def test_a_guest_is_sent_to_the_login_page(self):
        response = self.client.get(reverse("leaderboard:board"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("member_login"), response["Location"])

    def test_a_member_sees_the_board(self):
        self.visit_on(self.today)
        self.login()

        response = self.client.get(reverse("leaderboard:board"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Papan Peringkat")
        self.assertContains(response, "Cornelius Y. M.")

    def test_their_own_points_are_shown(self):
        self.visit_on(self.today)
        self.login()

        response = self.client.get(reverse("leaderboard:board"))

        self.assertContains(response, "Poin kamu")
        self.assertEqual(response.context["board"]["mine"]["total"], B.POINTS["visits"])

    def test_the_period_can_be_switched(self):
        self.login()

        response = self.client.get(reverse("leaderboard:board"), {"periode": "lifetime"})

        self.assertTrue(response.context["period"]["is_lifetime"])
        self.assertContains(response, "Sepanjang Waktu")

    def test_a_bad_period_does_not_error(self):
        self.login()

        response = self.client.get(reverse("leaderboard:board"), {"periode": "../etc"})

        self.assertEqual(response.status_code, 200)

    def test_an_empty_month_says_so_instead_of_looking_broken(self):
        self.login()

        response = self.client.get(reverse("leaderboard:board"))

        self.assertContains(response, "Belum ada poin")


class ShareTest(BoardTestCase):
    """The bar behind each row: how far along the leader's total they are."""

    def test_the_leader_is_full_width(self):
        self.visit_on(self.today)

        self.assertEqual(B.compute(self.this_month)[0]["share"], 100)

    def test_others_are_proportional(self):
        other = self.a_member("half@example.com", "628590000001", "Half Member")
        for _ in range(4):
            self.visit_on(self.today, member=other)
        self.visit_on(self.today)

        rows = B.compute(self.this_month)

        self.assertEqual(rows[0]["share"], 100)
        self.assertEqual(rows[1]["share"], 25)

    def test_a_negative_total_cannot_draw_a_bar(self):
        other = self.a_member("neg@example.com", "628590000002", "Negative Member")
        self.visit_on(self.today)
        instance = self.class_on(self.today - timedelta(days=1))
        ClassMiss.objects.create(
            member=other,
            class_instance=instance,
            class_date=instance.date,
            class_name="Kelas Pemula",
        )

        rows = B.compute(self.this_month)
        negative = next(row for row in rows if row["member_id"] == other.id)

        self.assertLess(negative["total"], 0)
        self.assertEqual(negative["share"], 0)

    def test_a_board_where_everyone_is_negative_does_not_divide_by_zero(self):
        instance = self.class_on(self.today - timedelta(days=1))
        ClassMiss.objects.create(
            member=self.member,
            class_instance=instance,
            class_date=instance.date,
            class_name="Kelas Pemula",
        )

        rows = B.compute(self.this_month)

        self.assertEqual(rows[0]["share"], 0)
