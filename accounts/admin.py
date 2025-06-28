from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from visits.admin import admin_site
from .models import Member, User, Tamu, Masukkan


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


class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone_number",
        "formatted_active_until",
        "formatted_pemula_active_until",
        "formatted_semi_private_active_until",
        "pt_session_count",
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
        (
            "Membership Information",
            {
                "fields": (
                    "active_until",
                    "pemula_active_until",
                    "semi_private_active_until",
                    "pt_session_count",
                )
            },
        ),
        ("Additional Information", {"fields": ("goals", "know_mulai_gym_from")}),
    )

    def formatted_active_until(self, obj):
        if obj.active_until:
            return timezone.localtime(obj.active_until).strftime("%d %b %Y")
        return "-"

    formatted_active_until.short_description = "Active Until"

    def formatted_pemula_active_until(self, obj):
        if obj.pemula_active_until:
            return timezone.localtime(obj.pemula_active_until).strftime("%d %b %Y")
        return "-"

    formatted_pemula_active_until.short_description = "Pemula Active Until"

    def formatted_semi_private_active_until(self, obj):
        if obj.semi_private_active_until:
            return timezone.localtime(obj.semi_private_active_until).strftime(
                "%d %b %Y"
            )
        return "-"

    formatted_semi_private_active_until.short_description = "Semi Private Active Until"

    def membership_status(self, obj):
        if obj.is_active_member:
            return "Active"
        return "Expired"

    membership_status.short_description = "Status"


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


class MasukkanAdmin(admin.ModelAdmin):
    list_display = ("get_display_name", "contact", "feedback_snippet", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "contact", "feedback")
    readonly_fields = ("created_at",)
    list_display_links = ("get_display_name",)

    def get_display_name(self, obj):
        return obj.name or f"Feedback #{obj.id}"

    get_display_name.short_description = "Name"
    get_display_name.admin_order_field = "name"

    def feedback_snippet(self, obj):
        return obj.feedback[:50] + "..." if len(obj.feedback) > 50 else obj.feedback

    feedback_snippet.short_description = "Feedback"


admin_site.register(User, CustomUserAdmin)
admin_site.register(Member, MemberAdmin)
admin_site.register(Tamu, TamuAdmin)
admin_site.register(Masukkan, MasukkanAdmin)
