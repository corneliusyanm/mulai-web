from django.contrib import admin
from django.utils import timezone

from visits.admin import admin_site

from .models import ChapterProgress, QuizAnswer


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
