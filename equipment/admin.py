from django.contrib import admin
from .models import Equipment
from visits.admin import admin_site  # Import the custom admin site


class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "muscle_group", "video_link", "created_at")
    search_fields = ("name", "muscle_group")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


# Register the model with the custom admin site instead of the default one
admin_site.register(Equipment, EquipmentAdmin)
