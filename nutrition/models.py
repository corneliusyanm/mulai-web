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


class DailyQuestion(models.Model):
    """One question from the daily rotation.

    Seeded from `nutrition/daily_questions.py` by a migration, then editable in
    `/admin`. Which question lands on which day comes from `position` and the
    rotation in `nutrition/daily.py`, not from a date on the row: a fixed date per
    question would run out, and the whole point is that there is always one
    waiting tomorrow.
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Kode tetap, dipakai buat nyocokin jawaban yang udah tercatat. Jangan diubah.",
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text="Urutan dalam rotasi. Kosongkan (0) buat ditaruh paling akhir.",
    )
    question = models.TextField()
    choices = models.JSONField(
        help_text='Bentuknya [{"key": "a", "text": "..."}, ...]',
    )
    answer = models.CharField(max_length=8, help_text="Key jawaban yang benar, misal b")
    explanation = models.TextField()
    is_active = models.BooleanField(
        default=True,
        help_text="Matikan buat ngeluarin soal ini dari rotasi tanpa menghapusnya.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Soal Harian"
        verbose_name_plural = "Soal Harian"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["is_active", "position"])]

    def __str__(self):
        return f"{self.code}: {self.question[:60]}"

    def save(self, *args, **kwargs):
        if not self.position:
            last = DailyQuestion.objects.order_by("-position").first()
            self.position = (last.position if last else 0) + 1
        super().save(*args, **kwargs)

    @classmethod
    def rotation(cls):
        """The questions in rotation order, newest additions last."""
        return cls.objects.filter(is_active=True).order_by("position", "id")

    def choice_text(self, key):
        for choice in self.choices or []:
            if choice.get("key") == key:
                return choice.get("text", "")
        return ""


class DailyAnswer(models.Model):
    """A member's one answer for one day.

    Unique per (member, answer_date), which is the whole rule: one shot, no
    changing it once the explanation is on screen.

    `answer_date` is stored rather than derived from `created_at` so the day is
    unambiguous in Asia/Jakarta and the streak query is a plain date range.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="daily_answers"
    )
    question = models.ForeignKey(
        DailyQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    answer_date = models.DateField()
    chosen = models.CharField(max_length=8, blank=True)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Jawaban Harian"
        verbose_name_plural = "Jawaban Harian"
        ordering = ["-answer_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "answer_date"], name="one_daily_answer_per_day"
            )
        ]
        indexes = [
            models.Index(fields=["member", "answer_date"]),
            models.Index(fields=["question"]),
        ]

    def __str__(self):
        mark = "benar" if self.is_correct else "salah"
        return f"{self.member.name} {self.answer_date} ({mark})"
