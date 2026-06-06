from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from visits.admin import admin_site

from .models import Announcement


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "message_short",
        "level",
        "status_badge",
        "starts_at",
        "ends_at",
        "priority",
        "is_active",
    )
    list_editable = ("priority", "is_active")
    list_filter = ("level", "is_active")
    search_fields = ("message",)
    ordering = ("-priority", "-starts_at")
    fields = ("message", "level", "starts_at", "ends_at", "priority", "is_active")

    @admin.display(description="Pesan")
    def message_short(self, obj):
        return obj.message if len(obj.message) <= 60 else obj.message[:57] + "..."

    @admin.display(description="Status")
    def status_badge(self, obj):
        now = timezone.now()
        if not obj.is_active:
            label, color = "Nonaktif", "#6c757d"
        elif obj.starts_at > now:
            label, color = "Terjadwal", "#0d6efd"
        elif obj.ends_at < now:
            label, color = "Berakhir", "#6c757d"
        else:
            label, color = "Tayang", "#198754"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;white-space:nowrap;">{}</span>',
            color,
            label,
        )


admin_site.register(Announcement, AnnouncementAdmin)
