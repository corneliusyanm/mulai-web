from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import Class, ClassSchedule, ClassInstance


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
