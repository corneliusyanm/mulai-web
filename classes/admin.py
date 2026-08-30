from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import (
    BookingPenalty,
    Class,
    ClassInstance,
    ClassMiss,
    ClassSchedule,
    GymClosure,
    PenaltySettings,
)


class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1


class ActiveStatusFilter(SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("OPEN", "Open for Booking"),
            ("FULL", "Full"),
            ("COMPLETED", "Completed"),
            ("CANCELLED", "Cancelled"),
        )

    def queryset(self, request, queryset):
        if self.value() == "OPEN":
            return queryset.filter(status="OPEN")
        elif self.value() == "FULL":
            return queryset.filter(status="FULL")
        elif self.value() == "COMPLETED":
            return queryset.filter(status="COMPLETED")
        elif self.value() == "CANCELLED":
            return queryset.filter(status="CANCELLED")
        else:
            # Default: show only OPEN and FULL
            return queryset.filter(status__in=["OPEN", "FULL"])


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "max_members")
    inlines = [ClassScheduleInline]


@admin.register(ClassInstance)
class ClassInstanceAdmin(admin.ModelAdmin):
    list_display = ("class_schedule", "date", "start_time", "status", "available_slots")
    list_filter = ("date", ActiveStatusFilter)
    filter_horizontal = ("booked_members", "waitlisted_members")

    def available_slots(self, obj):
        return obj.available_slots

    available_slots.short_description = "Available Slots"


class GymClosureAdmin(admin.ModelAdmin):
    """Mark a day off before the cron has made anything to cancel."""

    list_display = ("start_date", "end_date", "what", "reason")
    list_filter = ("start_date", "class_obj")
    search_fields = ("reason",)
    date_hierarchy = "start_date"
    readonly_fields = ("created_at",)

    def what(self, obj):
        return obj.class_obj.name if obj.class_obj else "Semua kelas"

    what.short_description = "Kelas"

    def save_model(self, request, obj, form, change):
        """Save, then report what it cleared, since the model does it silently."""
        from django.contrib import messages as django_messages

        super().save_model(request, obj, form, change)
        # save() already cancelled them; count what is now cancelled in the range
        # so the admin sees whether anyone has to be contacted.
        cancelled = ClassInstance.objects.filter(
            date__gte=obj.start_date, date__lte=obj.end_date, status="CANCELLED"
        )
        if obj.class_obj_id:
            cancelled = cancelled.filter(class_schedule__class_obj_id=obj.class_obj_id)
        count = cancelled.count()
        if count:
            django_messages.warning(
                request,
                f"{count} kelas di tanggal itu sudah terlanjur dibuat dan sekarang "
                f"dibatalkan. Cek Reminder, member yang sudah booking ada di sana.",
            )


class PenaltySettingsAdmin(admin.ModelAdmin):
    """One row, edited in place. These are the numbers being experimented with."""

    list_display = (
        "enabled",
        "advance_classes_per_day",
        "extra_booking_minutes",
        "late_cancel_hours",
        "window_days",
        "misses_allowed",
        "ban_days",
        "effective_from",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Singleton: the row is created by a migration, so adding a second one
        # would just make it ambiguous which set of rules is live.
        return not PenaltySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ClassMissAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "class_name",
        "class_date",
        "class_start_time",
        "kind",
        "recorded_at",
    )
    list_filter = ("kind", "class_date", "class_name")
    search_fields = ("member__name", "member__email", "member__phone_number")
    date_hierarchy = "class_date"
    readonly_fields = ("recorded_at",)
    autocomplete_fields = ()

    def has_add_permission(self, request):
        # Written by the nightly command from real bookings and check-ins. Typing
        # one by hand would make a member's record disagree with what happened.
        return False


class BookingPenaltyAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "starts_on",
        "blocked_until",
        "miss_days",
        "bookings_cancelled",
        "waitlists_cleared",
        "active_now",
    )
    list_filter = ("starts_on",)
    search_fields = ("member__name", "member__email", "member__phone_number")
    date_hierarchy = "starts_on"
    readonly_fields = ("created_at",)

    def active_now(self, obj):
        return obj.is_active()

    active_now.boolean = True
    active_now.short_description = "Sedang berjalan"

    def has_add_permission(self, request):
        return False
