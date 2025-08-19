from django.contrib import admin
from django.core.cache import cache
from .models import Equipment
from visits.admin import admin_site  # Import the custom admin site


class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "muscle_group",
        "total_views",
        "authenticated_views",
        "anonymous_views",
        "engagement_rate",
        "created_at",
    )
    search_fields = ("name", "muscle_group")
    list_filter = ("muscle_group", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-total_views", "name")  # Order by most viewed first
    readonly_fields = ("total_views", "authenticated_views", "anonymous_views")

    fieldsets = (
        (None, {"fields": ("name", "slug", "muscle_group", "detailed_muscle_group")}),
        ("Content", {"fields": ("description", "video_link")}),
        (
            "Analytics",
            {
                "fields": ("total_views", "authenticated_views", "anonymous_views"),
                "classes": ("collapse",),
            },
        ),
    )

    def engagement_rate(self, obj):
        """Calculate percentage of authenticated vs total views"""
        if obj.total_views == 0:
            return "0%"
        rate = (obj.authenticated_views / obj.total_views) * 100
        return f"{rate:.1f}%"

    engagement_rate.short_description = "Member Engagement"
    engagement_rate.admin_order_field = "authenticated_views"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Clear equipment list cache when equipment is modified
        cache.delete("equipment_grouped_list")

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        # Clear equipment list cache when equipment is deleted
        cache.delete("equipment_grouped_list")

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        # Clear equipment list cache when multiple equipment are deleted
        cache.delete("equipment_grouped_list")


# Register the model with the custom admin site instead of the default one
admin_site.register(Equipment, EquipmentAdmin)
