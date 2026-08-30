"""Reorder the unshown daily questions so consecutive days change topic.

The rotation walked `daily_questions.py` in file order, and that file is grouped
by topic for whoever reviews it. One question a day turned each group into a run:
twelve days of calories, twelve of protein, ten of drinks, and weight training
not until day 55. It reads like the same question every morning, which is the
opposite of the point.

What moves and what does not:

- **Positions 1 to 30 stay exactly as they are.** The rotation started 1 Aug 2026
  and reached position 30 today, 30 Aug, so those are the days members have
  already had, today's included. Moving today's question out from under the
  people who have already answered it would show them a new question with their
  old answer marked on it, until midnight.
- **Anything with a recorded answer stays too**, on the same reasoning, in case
  this reaches production a few days later than intended. Then only the questions
  nobody has seen move, and the frozen ones keep the slot they were shown in.
- The rest are dealt into the leftover slots by `interleave_topics`, starting from
  a topic that is not the one showing today.

Reordering again later means bumping `FROZEN_THROUGH` to whatever position the
rotation has reached by then. Everything before it has been spent.
"""

from django.db import migrations

from nutrition.daily_questions import TOPIC_OF
from nutrition.interleave import interleave_topics

# Day 30 of the rotation, 30 Aug 2026. Hard-coded rather than worked out from
# today's date so that a database built next year lands on the same order as
# production, and so the tests are not reading a calendar.
FROZEN_THROUGH = 30


def spread(apps, schema_editor):
    DailyQuestion = apps.get_model("nutrition", "DailyQuestion")
    DailyAnswer = apps.get_model("nutrition", "DailyAnswer")

    questions = list(DailyQuestion.objects.order_by("position", "id"))
    answered = set(DailyAnswer.objects.values_list("question__code", flat=True))

    def is_frozen(index, code):
        # Anything unknown to the module stays where it is too: it can only have
        # come from /admin, and nothing here knows what it is about.
        return index <= FROZEN_THROUGH or code in answered or code not in TOPIC_OF

    at = {index: question for index, question in enumerate(questions, start=1)}
    slots = [index for index, q in at.items() if not is_frozen(index, q.code)]
    if not slots:
        return

    late = [
        q.code for index, q in at.items() if index > FROZEN_THROUGH and q.code in answered
    ]
    if late:
        print(
            f"\n  Shown already, past position {FROZEN_THROUGH}, so left where "
            f"they are: {', '.join(late)}"
        )

    # The topic showing the day before the first slot that moves, so the join does
    # not put two of the same topic together.
    before = at.get(slots[0] - 1)
    after = TOPIC_OF.get(before.code) if before else None

    moving = [at[index].code for index in slots]
    by_code = {question.code: question for question in questions}
    for slot, code in zip(slots, interleave_topics(moving, TOPIC_OF, after=after)):
        question = by_code[code]
        if question.position != slot:
            question.position = slot
            question.save()


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0005_harder_daily_questions"),
    ]

    # Not reversible: the file order it came from is still in `daily_questions.py`,
    # but putting it back would hand members the runs this exists to remove.
    operations = [migrations.RunPython(spread, migrations.RunPython.noop)]
