"""Kuis Harian: one question a day, one shot at it, then the explanation.

For members who have finished all nine chapters and would otherwise never open
the app again. A minute a day, something new, and a point on the leaderboard.

The rotation is `(day - ROTATION_EPOCH) % how many questions are active`, so
everybody gets the same question on the same day and it never runs out. Adding
questions shifts which day each one lands on, which does not matter: what matters
is that tomorrow has one.
"""

from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone

from .models import DailyAnswer, DailyQuestion

# Day zero of the rotation. Fixed so the question of the day is the same for
# everyone and does not move when the code is redeployed.
ROTATION_EPOCH = date(2026, 8, 1)

# Below this many answers, the "what everyone else picked" split is noise, and
# "100% picked this" off a single answer reads worse than showing nothing.
MIN_SPLIT_SAMPLE = 5

# How far back a streak is worth looking. Nobody needs to be told they answered
# every day for four months, and it keeps the query small.
STREAK_LOOKBACK_DAYS = 120


def question_for(day=None):
    """The question for a given local day, or None if none are active."""
    day = day or timezone.localdate()
    total = DailyQuestion.rotation().count()
    if not total:
        return None
    index = (day - ROTATION_EPOCH).days % total
    return DailyQuestion.rotation()[index]


def answer_for(member, day):
    if not member:
        return None
    return (
        DailyAnswer.objects.filter(member=member, answer_date=day)
        .select_related("question")
        .first()
    )


def streak(member, day=None):
    """Days in a row ending today, or ending yesterday if today is unanswered.

    Answering is what counts, not answering correctly: the habit is the point.
    Today being unanswered does not break a streak yet, otherwise every morning
    would show a zero.
    """
    if not member:
        return 0
    day = day or timezone.localdate()
    days = set(
        DailyAnswer.objects.filter(
            member=member,
            answer_date__gte=day - timedelta(days=STREAK_LOOKBACK_DAYS),
            answer_date__lte=day,
        ).values_list("answer_date", flat=True)
    )
    if not days:
        return 0

    cursor = day if day in days else day - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def choice_split(question):
    """{choice key: percent} across every answer this question has ever had.

    All-time rather than today only: the question comes round again every hundred
    days, and a bigger sample makes the number worth showing. Returns {} until
    there are enough answers to mean anything.
    """
    rows = (
        DailyAnswer.objects.filter(question=question)
        .exclude(chosen="")
        .values("chosen")
        .annotate(total=Count("id"))
    )
    counts = {row["chosen"]: row["total"] for row in rows}
    total = sum(counts.values())
    if total < MIN_SPLIT_SAMPLE:
        return {}
    return {key: round(value * 100 / total) for key, value in counts.items()}


def state_for(member, day=None, guest=None):
    """Everything the page and the teaser card need, or None with no questions.

    `guest` is the session record for somebody not logged in, so their answer
    reads exactly like a member's. Whether the answer came from the database or a
    session is flattened here, rather than left for a template to figure out, and
    each choice arrives carrying its own state so the markup stays dumb.
    """
    day = day or timezone.localdate()
    question = question_for(day)
    if not question:
        return None

    answer = answer_for(member, day) if member else None
    if answer:
        chosen, is_correct = answer.chosen, answer.is_correct
    elif guest:
        chosen, is_correct = guest.get("chosen", ""), bool(guest.get("is_correct"))
    else:
        chosen, is_correct = "", False

    answered = bool(answer or guest)
    split = choice_split(question) if answered else {}

    choices = [
        {
            "key": choice["key"],
            "text": choice["text"],
            "percent": split.get(choice["key"]),
            "is_answer": choice["key"] == question.answer,
            "is_chosen": choice["key"] == chosen,
        }
        for choice in question.choices or []
    ]

    return {
        "day": day,
        "question": question,
        "choices": choices,
        "answered": answered,
        "chosen": chosen,
        "is_correct": is_correct,
        "has_split": bool(split),
        "streak": streak(member, day),
        "total_answered": (
            DailyAnswer.objects.filter(member=member).count() if member else 0
        ),
    }


def grade(question, chosen):
    return bool(chosen) and chosen == question.answer


def record(member, day, question, chosen):
    """Store the one answer for the day, or return the existing one untouched.

    Returns (answer, created). The unique constraint is the real guard; this just
    means a double tap gets the first answer back rather than an error page.
    """
    existing = answer_for(member, day)
    if existing:
        return existing, False

    answer = DailyAnswer.objects.create(
        member=member,
        question=question,
        answer_date=day,
        chosen=chosen or "",
        is_correct=grade(question, chosen),
    )
    return answer, True


def sync_questions(question_model, rows):
    """Insert any question from `rows` that is not in the database yet.

    Used by the seeding migration and by any later migration that adds a batch.
    Matches on `code` and never overwrites, so wording edited in /admin survives
    a later migration running again.
    """
    existing = set(question_model.objects.values_list("code", flat=True))
    created = 0
    for row in rows:
        if row["code"] in existing:
            continue
        question_model.objects.create(**row)
        created += 1
    return created


def rewrite_questions(question_model, rows, codes):
    """Overwrite the wording, choices, answer and explanation of existing rows.

    `sync_questions` deliberately never overwrites, so editing a question in
    `daily_questions.py` after it has been seeded does nothing on its own. This is
    the other half: a migration passes the codes it means to rewrite.

    Codes rather than "everything in rows" on purpose. A recorded answer is only a
    letter, so rewriting the choices under a question that somebody has already
    answered would leave that letter pointing at different text, and the all-time
    split would mix two different questions. The caller decides, and is expected
    to leave out anything already answered.

    `position` is not touched, so which question lands on which day does not move.
    Codes that do not exist yet are skipped: inserting is `sync_questions`' job.
    """
    by_code = {row["code"]: row for row in rows}
    changed = 0
    for question in question_model.objects.filter(code__in=codes):
        row = by_code.get(question.code)
        if not row:
            continue
        question.question = row["question"]
        question.choices = row["choices"]
        question.answer = row["answer"]
        question.explanation = row["explanation"]
        question.save()
        changed += 1
    return changed
