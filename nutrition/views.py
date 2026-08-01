"""Belajar Gizi: read the chapters, answer the quiz, keep the progress.

Anyone can read. Progress, badges and the level are only for members, since
they need somebody to belong to. A guest gets the same content plus an invite
to sign in at the end.
"""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import Member

from . import content, progress
from .models import ChapterProgress, QuizAnswer

BLOCK_TEMPLATES = {
    "card": "nutrition/_block_card.html",
    "quiz": "nutrition/_block_quiz.html",
    "bars": "nutrition/_block_bars.html",
    "swap": "nutrition/_block_swap.html",
    "verdicts": "nutrition/_block_verdicts.html",
}


def _member(request):
    email = request.session.get("member_email")
    if not email:
        return None
    return Member.objects.filter(email=email).first()


def index(request):
    member = _member(request)
    summary = progress.summary(member)

    chapters = []
    for chapter in content.chapters():
        done = summary["by_chapter"].get(chapter["slug"])
        chapters.append(
            dict(
                chapter,
                done=done,
                medal=(
                    content.medal(done.best_correct, done.total) if done else None
                ),
            )
        )

    return render(
        request,
        "nutrition/index.html",
        {
            "member": member,
            "chapters": chapters,
            "summary": summary,
            "levels": content.level_chips(),
            # Reading time for the whole thing, so the lead line cannot drift
            # from the chapter list under it.
            "total_minutes": sum(c["minutes"] for c in content.CHAPTERS),
        },
    )


def _numbered(chapter):
    """The chapter's blocks with quiz blocks numbered, for "Soal 2 dari 4"."""
    quiz_number = 0
    numbered = []
    for block in chapter["blocks"]:
        if block["type"] == "quiz":
            quiz_number += 1
            numbered.append(dict(block, quiz_number=quiz_number))
        else:
            numbered.append(dict(block))
    return numbered


def _prepared(block, index):
    """Anything a block needs that a template cannot work out for itself.

    Django templates cannot subtract or take a max, so the bar scale and the
    before/after deltas are computed here rather than hard-coded in content.py
    where they would drift from the numbers above them.
    """
    prepared = dict(block, template=BLOCK_TEMPLATES[block["type"]], step=index + 1)

    if block["type"] == "bars":
        prepared["max"] = max([row["value"] for row in block["rows"]] + [1])

    if block["type"] == "swap":
        prepared["plates"] = [block["before"], block["after"]]
        prepared["delta_kcal"] = block["after"]["kcal"] - block["before"]["kcal"]
        prepared["delta_protein"] = (
            block["after"]["protein"] - block["before"]["protein"]
        )
        # The sign is a template decision, the magnitude is not: |cut:"-" would
        # need the number stringified first.
        prepared["delta_kcal_abs"] = abs(prepared["delta_kcal"])
        prepared["delta_protein_abs"] = abs(prepared["delta_protein"])

    return prepared


def chapter(request, slug):
    chapter = content.get_chapter(slug)
    if not chapter:
        raise Http404("Bab tidak ditemukan")

    member = _member(request)
    detail_url = request.build_absolute_uri(
        reverse("nutrition:chapter", args=[chapter["slug"]])
    )

    blocks = [_prepared(block, i) for i, block in enumerate(_numbered(chapter))]

    done = progress.by_chapter(member).get(slug)
    return render(
        request,
        "nutrition/chapter.html",
        {
            "member": member,
            "chapter": chapter,
            "blocks": blocks,
            "done": done,
            "next_chapter": content.next_chapter(slug),
            "disclaimer": content.DISCLAIMER,
            "trainer_url": content.trainer_whatsapp_url(chapter["title"]),
            "share_url": content.share_whatsapp_url(chapter["title"], detail_url),
        },
    )


@require_POST
def finish(request, slug):
    """Record a finished chapter. Answers are graded here, not in the browser.

    Returns the new level so the result screen can announce it. A guest gets
    `saved: false` and a nudge to sign in; nothing is stored for them.
    """
    chapter = content.get_chapter(slug)
    if not chapter:
        raise Http404("Bab tidak ditemukan")

    member = _member(request)
    try:
        payload = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"error": "invalid json"}, status=400)

    answers = payload.get("answers") or {}
    if not isinstance(answers, dict):
        return JsonResponse({"error": "invalid answers"}, status=400)

    graded = content.grade(chapter, answers)
    correct = sum(1 for row in graded if row["correct"])
    total = len(graded)

    if not member:
        return JsonResponse(
            {
                "saved": False,
                "correct": correct,
                "total": total,
                "medal": content.medal(correct, total),
            }
        )

    for row in graded:
        QuizAnswer.objects.create(
            member=member,
            chapter_slug=slug,
            question_key=row["key"],
            chosen=row["chosen"] or "",
            is_correct=row["correct"],
        )

    existing = ChapterProgress.objects.filter(member=member, chapter_slug=slug).first()
    if existing:
        existing.correct = correct
        existing.total = total
        existing.best_correct = max(existing.best_correct, correct)
        existing.attempts += 1
        existing.save()
    else:
        ChapterProgress.objects.create(
            member=member,
            chapter_slug=slug,
            correct=correct,
            total=total,
            best_correct=correct,
            attempts=1,
        )

    summary = progress.summary(member)
    return JsonResponse(
        {
            "saved": True,
            "correct": correct,
            "total": total,
            "medal": content.medal(correct, total),
            "level": summary["level"],
            "finished_count": summary["finished_count"],
            "total_chapters": summary["total_chapters"],
            "all_done": summary["all_done"],
        }
    )
