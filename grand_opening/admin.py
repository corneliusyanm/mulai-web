from django.contrib import admin

from accounts.admin import WhatsAppLinkMixin
from visits.admin import admin_site
from .models import GrandOpeningRegistration


class GrandOpeningRegistrationAdmin(WhatsAppLinkMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "whatsapp_link",
        "age",
        "visit_schedule",
        "gym_experience",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "phone_number", "social_media_username", "visit_schedule")
    readonly_fields = ("created_at",)


admin_site.register(GrandOpeningRegistration, GrandOpeningRegistrationAdmin)
