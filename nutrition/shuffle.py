"""Spread the correct answer across the choices instead of leaving it in the middle.

Writing questions by hand produces a tell. Authored as they were, 77 of the 100
daily questions had the answer at B and not one had it at C, so "always pick the
middle one" scored 77% without reading anything. The chapter quiz was worse: 31 of
36 at B. That defeats the point of asking.

The fix is a deterministic placement, not a shuffle at render time:

- **Derived from the question's `code`**, so a question's arrangement never
  changes once it exists. The answer recorded against it stays meaningful.
- **Independent per question**, so appending new questions leaves every existing
  one exactly where it was.
- **Not a pattern a member can learn.** Cycling a, b, c, a, b, c would be even but
  guessable from one day to the next, which is the same problem again.

Applied once at import in `content.py` and `daily_questions.py`, so every reader
(pages, grading, admin analytics) sees the same arrangement. One consequence worth
knowing: numeric options come out unsorted, e.g. 130 / 50 / 400. Sorted options
read a little tidier, but with the plausible value sitting in the middle they are
exactly what gave the answer away.
"""

from hashlib import md5

# Mixed into the hash. Picked from a few candidates for the flattest spread over
# the questions that exist today: the daily set lands 34/32/34 and the chapters
# 14/10/12, against 77/23/0 and 31/5/0 as authored. Fixed forever now, because
# changing it would rearrange every question and orphan the answers already
# recorded against them.
SALT = "mulai-gizi-2026-9"

LETTERS = "abcdefgh"


def place_answer(code, choices, answer_key):
    """Return (choices, answer_key) with the right answer moved to a stable slot.

    Choices come back relabelled a, b, c by their new position, and the wrong
    answers keep their relative order.
    """
    if not choices:
        return choices, answer_key

    correct = next((c for c in choices if c.get("key") == answer_key), None)
    if correct is None:
        # An answer that names no choice is a content bug, caught by the tests.
        # Leave it alone rather than quietly inventing an arrangement.
        return choices, answer_key

    others = [c for c in choices if c.get("key") != answer_key]
    digest = md5(f"{SALT}:{code}".encode()).hexdigest()
    target = int(digest, 16) % len(choices)

    ordered = others[:target] + [correct] + others[target:]
    placed = [
        {**choice, "key": LETTERS[index]} for index, choice in enumerate(ordered)
    ]
    return placed, LETTERS[target]
