from django.contrib import admin
from django.utils import timezone

from visits.admin import admin_site

from .models import ChapterProgress, DailyAnswer, DailyQuestion, QuizAnswer


class ChapterProgressAdmin(admin.ModelAdmin):
    list_display = ("member", "chapter_slug", "score", "attempts", "finished")
    list_filter = ("chapter_slug",)
    search_fields = ("member__name", "member__email", "member__phone_number")
    readonly_fields = ("first_finished_at", "last_finished_at")

    def score(self, obj):
        return f"{obj.best_correct}/{obj.total}"

    score.short_description = "Skor terbaik"

    def finished(self, obj):
        return timezone.localtime(obj.last_finished_at).strftime("%d %b %Y %H:%M")

    finished.short_description = "Terakhir selesai"


class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("member", "chapter_slug", "question_key", "chosen", "is_correct")
    list_filter = ("chapter_slug", "is_correct")
    search_fields = ("member__name", "question_key")

    def has_add_permission(self, request):
        return False


admin_site.register(ChapterProgress, ChapterProgressAdmin)
admin_site.register(QuizAnswer, QuizAnswerAdmin)


class DailyQuestionAdmin(admin.ModelAdmin):
    list_display = ("position", "code", "short_question", "answer", "is_active", "times_answered")
    list_filter = ("is_active",)
    search_fields = ("code", "question", "explanation")
    list_editable = ("position", "is_active")
    # position is first in list_display and editable, so something else has to be
    # the link into the row.
    list_display_links = ("code",)
    ordering = ("position", "id")
    readonly_fields = ("created_at", "updated_at")

    def short_question(self, obj):
        return obj.question[:70] + ("..." if len(obj.question) > 70 else "")

    short_question.short_description = "Soal"

    def times_answered(self, obj):
        return obj.answers.count()

    times_answered.short_description = "Dijawab"


class DailyAnswerAdmin(admin.ModelAdmin):
    list_display = ("member", "answer_date", "question_code", "chosen", "is_correct")
    list_filter = ("is_correct", "answer_date")
    search_fields = ("member__name", "member__email", "question__code")
    date_hierarchy = "answer_date"
    readonly_fields = ("created_at",)

    def question_code(self, obj):
        return obj.question.code

    question_code.short_description = "Soal"

    def has_add_permission(self, request):
        # One answer per member per day is the whole rule; typing one in by hand
        # would hand somebody a day they did not actually show up for.
        return False


admin_site.register(DailyQuestion, DailyQuestionAdmin)
admin_site.register(DailyAnswer, DailyAnswerAdmin)
