from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "reminder_type",
        "due_date",
        "created_date",
        "reminder_status",
    )
    list_filter = (
        "reminder_type",
        "is_resolved",
        ("due_date", DateFieldListFilter),
        ("created_date", DateFieldListFilter),
    )
    search_fields = ("member__name", "member__email", "member__phone_number", "reason")
    readonly_fields = ("created_date", "resolved_date")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("current/", self.current_reminders_view, name="current-reminders"),
            path("history/", self.reminder_history_view, name="reminder-history"),
            path(
                "resolve/<int:reminder_id>/",
                self.resolve_reminder,
                name="resolve-reminder",
            ),
        ]
        return custom_urls + urls

    def reminder_status(self, obj):
        if obj.is_resolved:
            return "Resolved"
        return "Active"

    reminder_status.short_description = "Status"

    def resolve_reminder(self, request, reminder_id):
        if not self.has_change_permission(request):
            raise PermissionDenied

        try:
            reminder = Reminder.objects.get(id=reminder_id, is_resolved=False)
            reminder.mark_resolved()
            messages.success(
                request, f"Successfully resolved reminder for {reminder.member.name}"
            )
        except Reminder.DoesNotExist:
            messages.error(request, "Reminder not found or already resolved")
        return redirect("admin:current-reminders")

    def current_reminders_view(self, request):
        reminders = Reminder.objects.filter(is_resolved=False).order_by(
            "due_date", "-created_date"
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Current Reminders",
            "reminders": reminders,
            "opts": self.model._meta,
            "current_view": "current",
            "has_change_permission": self.has_change_permission(request),
        }
        return render(
            request, "admin/reminders/reminder/current_reminders.html", context
        )

    def reminder_history_view(self, request):
        reminders = Reminder.objects.filter(is_resolved=True).order_by("-resolved_date")

        context = {
            **self.admin_site.each_context(request),
            "title": "Reminder History",
            "reminders": reminders,
            "opts": self.model._meta,
            "current_view": "history",
            "has_change_permission": self.has_change_permission(request),
        }
        return render(
            request, "admin/reminders/reminder/reminder_history.html", context
        )
