"""Who has read what, and which questions they get wrong.

Only progress lives in the database. The chapters themselves are in
`nutrition/content.py`, so a chapter is referenced by its slug and a question
by its key. Both are stable strings, never foreign keys.
"""

from django.db import models

from accounts.models import Member


class ChapterProgress(models.Model):
    """One row per member per chapter, rewritten on every finish.

    Keeps the best score as well as the latest, so a member who retakes a
    chapter and does worse does not lose the badge they earned.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="nutrition_progress"
    )
    chapter_slug = models.CharField(max_length=50)
    correct = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    best_correct = models.PositiveSmallIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    first_finished_at = models.DateTimeField(auto_now_add=True)
    last_finished_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Progres Bab"
        verbose_name_plural = "Progres Bab"
        constraints = [
            models.UniqueConstraint(
                fields=["member", "chapter_slug"], name="one_progress_per_chapter"
            )
        ]
        indexes = [models.Index(fields=["chapter_slug"])]
        ordering = ["-last_finished_at"]

    def __str__(self):
        return f"{self.member.name} - {self.chapter_slug} ({self.best_correct}/{self.total})"


class QuizAnswer(models.Model):
    """Every answer a member submits, kept for the admin insight page.

    The point is not the individual member, it is the aggregate: the question
    most people get wrong is the thing the trainers should explain on the floor.
    A member can answer the same question again on a retake, so the analytics
    counts each member's *first* answer per question.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="nutrition_answers"
    )
    chapter_slug = models.CharField(max_length=50)
    question_key = models.CharField(max_length=50)
    chosen = models.CharField(max_length=8, blank=True)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Jawaban Kuis"
        verbose_name_plural = "Jawaban Kuis"
        indexes = [
            models.Index(fields=["question_key"]),
            models.Index(fields=["member", "question_key"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        mark = "benar" if self.is_correct else "salah"
        return f"{self.member.name} - {self.question_key} ({mark})"
