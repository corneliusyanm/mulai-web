from django.contrib import admin
from .models import Class, ClassSchedule, ClassInstance


class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "max_members")
    inlines = [ClassScheduleInline]


@admin.register(ClassInstance)
class ClassInstanceAdmin(admin.ModelAdmin):
    list_display = ("class_schedule", "date", "start_time", "status", "available_slots")
    list_filter = ("date", "status")
    filter_horizontal = ("booked_members", "waitlisted_members")

    def available_slots(self, obj):
        return obj.available_slots

    available_slots.short_description = "Available Slots"
