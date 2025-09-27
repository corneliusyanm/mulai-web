from django.contrib import admin
from django.core.cache import cache
from django import forms
from .models import Equipment
from visits.admin import admin_site  # Import the custom admin site


class EquipmentAdminForm(forms.ModelForm):
    additional_videos_input = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "cols": 80}),
        required=False,
        help_text="Masukkan URL video tambahan, satu URL per baris. Contoh:\nhttps://www.youtube.com/watch?v=tcq5dX-ZcvA",
        label="Video Tambahan (URL)",
    )

    class Meta:
        model = Equipment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert JSON list to textarea string for editing
        if self.instance.pk and self.instance.additional_videos:
            urls = "\n".join(self.instance.additional_videos)
            self.fields["additional_videos_input"].initial = urls

        # Hide the actual JSON field from the form
        if "additional_videos" in self.fields:
            self.fields["additional_videos"].widget = forms.HiddenInput()

    def clean_additional_videos_input(self):
        urls_text = self.cleaned_data.get("additional_videos_input", "")
        if not urls_text:
            return []

        # Split by newlines and filter out empty lines
        urls = [url.strip() for url in urls_text.split("\n") if url.strip()]

        # Basic validation - check if URLs look like YouTube URLs
        youtube_domains = ["youtube.com", "youtu.be", "www.youtube.com"]
        for url in urls:
            if not any(domain in url for domain in youtube_domains):
                raise forms.ValidationError(
                    f"URL tidak valid: {url}. Hanya URL YouTube yang diperbolehkan."
                )

        return urls

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set the JSON field from the textarea input
        instance.additional_videos = self.cleaned_data.get(
            "additional_videos_input", []
        )
        if commit:
            instance.save()
        return instance


class EquipmentAdmin(admin.ModelAdmin):
    form = EquipmentAdminForm
    list_display = (
        "name",
        "muscle_group",
        "total_views",
        "authenticated_views",
        "anonymous_views",
        "engagement_rate",
        "additional_videos_count",
        "created_at",
    )
    search_fields = ("name", "muscle_group")
    list_filter = ("muscle_group", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-total_views", "name")  # Order by most viewed first
    readonly_fields = ("total_views", "authenticated_views", "anonymous_views")

    fieldsets = (
        (None, {"fields": ("name", "slug", "muscle_group", "detailed_muscle_group")}),
        (
            "Content",
            {"fields": ("description", "video_link", "additional_videos_input")},
        ),
        (
            "Analytics",
            {
                "fields": ("total_views", "authenticated_views", "anonymous_views"),
                "classes": ("collapse",),
            },
        ),
    )

    def additional_videos_count(self, obj):
        """Display count of additional videos"""
        if obj.additional_videos:
            count = len(obj.additional_videos)
            return f"{count} video{'s' if count != 1 else ''}"
        return "0 videos"

    additional_videos_count.short_description = "Video Tambahan"

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
