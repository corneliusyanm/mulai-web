"""Rewrite dq-007 to dq-100 as harder, four-choice questions.

The first hundred were written to be answerable in about five seconds, and they
were: three choices, and the answer usually the one plausible number in the
middle. `dq-101` onwards set a better bar (four choices, and an answer that needs
arithmetic, judgment or unlearning), so this brings the rest of the set up to it.

`sync_questions` never overwrites, which is right for wording fixed in /admin but
means editing `daily_questions.py` alone does nothing to a database that has
already been seeded. Hence `rewrite_questions`.

Why this is safe to run in place rather than retiring the codes and appending new
ones: the rotation started 2026-08-01 and moves one question a day, so when this
was written only dq-001 to dq-006 had ever been shown. Everything from dq-007 on
had zero recorded answers and nothing had been edited in /admin (checked against
production: `updated_at` equal to `created_at` on all 115 rows).

The guard below keeps that true whenever this actually runs. A recorded answer is
only a letter, so rewriting the choices under an answered question would leave
that letter pointing at different text and mix two different questions into one
all-time split. If the deploy slips by a few days, the questions that have gone
past keep their original wording and get named in the deploy log. Giving one of
those the harder treatment later needs a new code, not another rewrite.
"""

from django.db import migrations

from nutrition.daily import rewrite_questions
from nutrition.daily_questions import QUESTIONS

# dq-001 to dq-006 stay as they are: members have answered them.
FIRST_REWRITTEN = 6
LAST_REWRITTEN = 100


def rewrite(apps, schema_editor):
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    DailyAnswer = apps.get_model("nutrition", "DailyAnswer")

    answered = set(
        DailyAnswer.objects.values_list("question__code", flat=True).distinct()
    )
    wanted = [
        row["code"]
        for row in QUESTIONS
        if FIRST_REWRITTEN < row["position"] <= LAST_REWRITTEN
    ]
    skipped = [code for code in wanted if code in answered]
    if skipped:
        print(
            f"\n  Keeping the original wording of {len(skipped)} already answered "
            f"question(s): {', '.join(skipped)}"
        )

    rewrite_questions(
        DailyQuestion, QUESTIONS, [code for code in wanted if code not in answered]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0004_seed_daily_questions_ageing"),
    ]

    # Not reversible: the old wording only exists in git history, and putting it
    # back would mean carrying a hundred dead questions in this file forever.
    operations = [migrations.RunPython(rewrite, migrations.RunPython.noop)]
