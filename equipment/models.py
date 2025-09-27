from django.db import models
from django.utils.text import slugify
from urllib.parse import urlparse, parse_qs
import json


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    video_link = models.URLField()
    additional_videos = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional video URLs for tips and detailed explanations",
    )
    muscle_group = models.CharField(max_length=50, blank=True)
    detailed_muscle_group = models.CharField(max_length=100, blank=True)

    # View analytics
    total_views = models.PositiveIntegerField(
        default=0, help_text="Total number of page views"
    )
    authenticated_views = models.PositiveIntegerField(
        default=0, help_text="Views from logged-in users"
    )
    anonymous_views = models.PositiveIntegerField(
        default=0, help_text="Views from anonymous users"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_youtube_video_id(self):
        """
        Extracts the YouTube video ID from various URL formats.
        Supports standard, shortened, and embed URLs.
        """
        if "youtube.com/embed" in self.video_link:
            # Extract ID from embed URL
            return self.video_link.split("/embed/")[1].split("?")[0]

        parsed_url = urlparse(self.video_link)
        if "youtu.be" in parsed_url.netloc:
            video_id = parsed_url.path[1:]
        else:
            query_params = parse_qs(parsed_url.query)
            video_id = query_params.get("v", [None])[0]

        return video_id

    def get_youtube_embed_url(self):
        """
        Extracts the YouTube video ID and returns the embed URL.
        Supports standard, shortened, and embed URLs.
        """
        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    def get_youtube_thumbnail_url(self, quality="hqdefault"):
        """
        Returns YouTube thumbnail URL for the video.
        Quality options: 'default', 'hqdefault', 'mqdefault', 'sddefault', 'maxresdefault'
        """
        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        return None

    def get_additional_video_data(self):
        """
        Process additional video URLs and return structured data with video IDs,
        embed URLs, and thumbnail URLs.
        """
        if not self.additional_videos:
            return []

        video_data = []
        for url in self.additional_videos:
            if url and isinstance(url, str):
                video_id = self._extract_youtube_video_id(url)
                if video_id:
                    video_data.append(
                        {
                            "url": url,
                            "video_id": video_id,
                            "embed_url": f"https://www.youtube.com/embed/{video_id}",
                            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                        }
                    )
        return video_data

    def _extract_youtube_video_id(self, url):
        """
        Helper method to extract YouTube video ID from any URL format.
        Similar to get_youtube_video_id but works with any URL string.
        """
        if not url:
            return None

        if "youtube.com/embed" in url:
            return url.split("/embed/")[1].split("?")[0]

        parsed_url = urlparse(url)
        if "youtu.be" in parsed_url.netloc:
            return parsed_url.path[1:]
        else:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]

    def increment_view_count(self, is_authenticated=False):
        """
        Increment the view count for this equipment.
        Uses F() expression to avoid race conditions.
        """
        from django.db.models import F

        if is_authenticated:
            Equipment.objects.filter(pk=self.pk).update(
                total_views=F("total_views") + 1,
                authenticated_views=F("authenticated_views") + 1,
            )
        else:
            Equipment.objects.filter(pk=self.pk).update(
                total_views=F("total_views") + 1,
                anonymous_views=F("anonymous_views") + 1,
            )

        # Refresh the instance to get updated values
        self.refresh_from_db(
            fields=["total_views", "authenticated_views", "anonymous_views"]
        )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
