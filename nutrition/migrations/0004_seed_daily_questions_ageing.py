"""Add the umur-panjang-vs-sehat batch of daily questions (dq-101 to dq-115).

Same helper as the first seeding: matched on `code`, never overwritten, so this
only inserts what is missing and leaves wording edited in /admin alone.
"""

from django.db import migrations

from nutrition.daily import sync_questions
from nutrition.daily_questions import QUESTIONS


def seed(apps, schema_editor):
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    sync_questions(DailyQuestion, QUESTIONS)


def unseed(apps, schema_editor):
    # Only this batch: the first hundred belong to 0003.
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    codes = [row["code"] for row in QUESTIONS if row["position"] > 100]
    DailyQuestion.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0003_seed_daily_questions"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
