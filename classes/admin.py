from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import (
    BookingPenalty,
    Class,
    ClassInstance,
    ClassMiss,
    ClassSchedule,
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


class PenaltySettingsAdmin(admin.ModelAdmin):
    """One row, edited in place. These are the numbers being experimented with."""

    list_display = (
        "enabled",
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
    list_display = ("member", "class_name", "class_date", "class_start_time", "recorded_at")
    list_filter = ("class_date", "class_name")
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
