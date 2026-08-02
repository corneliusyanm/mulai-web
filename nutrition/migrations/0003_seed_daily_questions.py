"""Seed the 100 daily questions from nutrition/daily_questions.py.

The rows are matched on `code` and never overwritten, so wording fixed in /admin
survives this running again, and a later migration can add a new batch by calling
the same helper with the same list.
"""

from django.db import migrations

from nutrition.daily import sync_questions
from nutrition.daily_questions import QUESTIONS


def seed(apps, schema_editor):
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    sync_questions(DailyQuestion, QUESTIONS)


def unseed(apps, schema_editor):
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    codes = [row["code"] for row in QUESTIONS]
    DailyQuestion.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0002_dailyquestion_dailyanswer_and_more"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
