from django.contrib import admin

from visits.admin import admin_site

from .models import ReviewSummary, Testimonial


class ReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ("rating", "review_count", "maps_url", "updated_at")
    fields = ("rating", "review_count", "maps_url")

    def has_add_permission(self, request):
        # One row only: the badge is a single pair of numbers for the whole site.
        return not ReviewSummary.objects.exists()


class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "author_name",
        "stars_display",
        "text_short",
        "priority",
        "is_active",
    )
    list_editable = ("priority", "is_active")
    list_filter = ("is_active", "rating")
    search_fields = ("author_name", "text")
    fields = ("author_name", "rating", "text", "review_url", "priority", "is_active")

    @admin.display(description="Rating")
    def stars_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @admin.display(description="Ulasan")
    def text_short(self, obj):
        return obj.text if len(obj.text) <= 80 else obj.text[:77] + "..."


admin_site.register(ReviewSummary, ReviewSummaryAdmin)
admin_site.register(Testimonial, TestimonialAdmin)
