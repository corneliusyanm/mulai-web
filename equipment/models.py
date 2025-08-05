from django.db import models
from django.utils.text import slugify
from urllib.parse import urlparse, parse_qs


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    video_link = models.URLField()
    muscle_group = models.CharField(max_length=50, blank=True)
    detailed_muscle_group = models.CharField(max_length=100, blank=True)

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

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
