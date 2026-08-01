"""What members actually understood, for the admin.

The useful output is not who scored what, it is which question the most people
got wrong: that is the thing worth explaining on the gym floor.

Kept out of `admin.py` so `visits/admin.py` can import the view without a
circular import (nutrition's admin imports the shared admin site from visits).
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render

from . import content
from .models import ChapterProgress, QuizAnswer


def first_answers():
    """Each member's first answer per question.

    A retake would otherwise flatter the numbers: somebody who got it wrong,
    read the explanation and answered again would count as understanding it all
    along. The first attempt is the honest one. Postgres `DISTINCT ON`, which
    the admin analytics already rely on elsewhere.
    """
    return (
        QuizAnswer.objects.order_by("member_id", "question_key", "created_at", "id")
        .distinct("member_id", "question_key")
    )


def question_stats():
    """Every quiz question with its first-attempt miss rate, worst first."""
    answers = list(first_answers().values("question_key", "chosen", "is_correct"))

    tally = {}
    for answer in answers:
        row = tally.setdefault(
            answer["question_key"], {"answered": 0, "wrong": 0, "picks": {}}
        )
        row["answered"] += 1
        if not answer["is_correct"]:
            row["wrong"] += 1
        if answer["chosen"]:
            row["picks"][answer["chosen"]] = row["picks"].get(answer["chosen"], 0) + 1

    stats = []
    for chapter in content.CHAPTERS:
        for block in chapter["blocks"]:
            if block["type"] != "quiz":
                continue
            counted = tally.get(block["key"], {"answered": 0, "wrong": 0, "picks": {}})
            choices = {choice["key"]: choice["text"] for choice in block["choices"]}

            # The wrong answer most people fall for says more than the miss rate
            # on its own: it names the misunderstanding.
            wrong_picks = {
                key: count
                for key, count in counted["picks"].items()
                if key != block["answer"]
            }
            top_wrong = max(wrong_picks, key=wrong_picks.get) if wrong_picks else None

            stats.append(
                {
                    "chapter": chapter["title"],
                    "key": block["key"],
                    "question": block["question"],
                    "answer_text": choices.get(block["answer"], block["answer"]),
                    "answered": counted["answered"],
                    "wrong": counted["wrong"],
                    "miss_percent": (
                        round(counted["wrong"] * 100 / counted["answered"])
                        if counted["answered"]
                        else 0
                    ),
                    "top_wrong_text": choices.get(top_wrong) if top_wrong else None,
                    "top_wrong_count": wrong_picks.get(top_wrong, 0) if top_wrong else 0,
                }
            )

    stats.sort(key=lambda row: (-row["miss_percent"], -row["answered"]))
    return stats


def chapter_stats():
    """Per chapter: how many members finished it and how well.

    One query for every chapter, grouped here. Scores are the member's best,
    not their latest, matching the badge they keep.
    """
    scores = {}
    for slug, best, total in ChapterProgress.objects.values_list(
        "chapter_slug", "best_correct", "total"
    ):
        scores.setdefault(slug, []).append((best, total))

    stats = []
    for chapter in content.chapters():
        rows = scores.get(chapter["slug"], [])
        stats.append(
            {
                "number": chapter["number"],
                "title": chapter["title"],
                "quiz_count": chapter["quiz_count"],
                "members": len(rows),
                "average_correct": (
                    round(sum(best for best, _ in rows) / len(rows), 1)
                    if rows
                    else None
                ),
                "perfect": sum(1 for best, total in rows if total and best == total),
            }
        )
    return stats


@staff_member_required
def nutrition_analytics_view(request):
    members_started = (
        ChapterProgress.objects.values("member_id").distinct().count()
    )
    all_done = (
        ChapterProgress.objects.values("member_id")
        .annotate(done=Count("chapter_slug", distinct=True))
        .filter(done__gte=content.total_chapters())
        .count()
    )

    recent = (
        ChapterProgress.objects.select_related("member")
        .order_by("-last_finished_at")[:25]
    )

    return render(
        request,
        "admin/analytics/belajar_gizi.html",
        {
            "title": "Belajar Gizi",
            "members_started": members_started,
            "members_all_done": all_done,
            "total_chapters": content.total_chapters(),
            "answers_recorded": QuizAnswer.objects.count(),
            "chapter_stats": chapter_stats(),
            "question_stats": question_stats(),
            "recent": recent,
        },
    )
