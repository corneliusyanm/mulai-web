from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from visits.admin import admin_site
from .models import Member, User, Tamu


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "user_type")
    list_filter = ("user_type",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "user_type",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone_number",
        "formatted_active_until",
        "membership_status",
        "created_at",
    )
    list_filter = ("gender", "created_at")
    search_fields = ("name", "email", "phone_number")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Basic Information", {"fields": ("name", "email", "phone_number", "gender")}),
        (
            "Physical Information",
            {"fields": ("age", "height", "weight", "years_of_working_out")},
        ),
        ("Membership Information", {"fields": ("active_until",)}),
        ("Additional Information", {"fields": ("goals", "know_mulai_gym_from")}),
    )

    def formatted_active_until(self, obj):
        if obj.active_until:
            return timezone.localtime(obj.active_until).strftime("%d %b %Y")
        return "-"

    formatted_active_until.short_description = "Active Until"

    def membership_status(self, obj):
        if obj.is_active_member:
            return "Active"
        return "Expired"

    membership_status.short_description = "Status"


@admin.register(Tamu)
class TamuAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "has_worked_out_before",
        "social_media_username",
        "created_at",
    )
    list_filter = ("has_worked_out_before", "created_at")
    search_fields = ("name", "phone_number", "social_media_username")
    readonly_fields = ("created_at",)


admin_site.register(User, CustomUserAdmin)
admin_site.register(Member, MemberAdmin)
admin_site.register(Tamu, TamuAdmin)
