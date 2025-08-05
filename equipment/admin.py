from django.contrib import admin
from django.core.cache import cache
from .models import Equipment
from visits.admin import admin_site  # Import the custom admin site


class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "muscle_group", "video_link", "created_at")
    search_fields = ("name", "muscle_group")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

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
