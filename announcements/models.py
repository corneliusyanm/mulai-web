from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    """A short, time-boxed message shown to visitors on the public site.

    An announcement is shown on the user-facing site only when BOTH:
      - ``is_active`` is True (manual on/off switch), AND
      - the current time is within ``starts_at`` .. ``ends_at`` (display window).

    Times are stored in UTC and interpreted in Asia/Jakarta on the admin form
    (``USE_TZ = True``).
    """

    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        IMPORTANT = "IMPORTANT", "Penting"
        URGENT = "URGENT", "Darurat"

    message = models.CharField(
        "Pesan",
        max_length=280,
        help_text="Pesan singkat yang tampil di banner (maks 280 karakter).",
    )
    level = models.CharField(
        "Tingkat",
        max_length=10,
        choices=Level.choices,
        default=Level.INFO,
        help_text="Info = hijau (cocok untuk promo), Penting = kuning, Darurat = merah.",
    )
    starts_at = models.DateTimeField(
        "Mulai tampil",
        help_text="Banner mulai tampil pada waktu ini (WIB).",
    )
    ends_at = models.DateTimeField(
        "Berhenti tampil",
        help_text="Banner berhenti tampil pada waktu ini (WIB).",
    )
    is_active = models.BooleanField(
        "Aktif",
        default=True,
        help_text="Matikan untuk menyembunyikan tanpa menghapus.",
    )
    priority = models.IntegerField(
        "Prioritas",
        default=0,
        help_text="Angka lebih besar tampil lebih dulu saat ada beberapa pengumuman.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pengumuman"
        verbose_name_plural = "Pengumuman"
        ordering = ["-priority", "-starts_at"]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.message[:50]}"

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "Waktu berhenti harus setelah waktu mulai."}
            )

    @property
    def is_live(self):
        """True if this announcement should be visible right now."""
        now = timezone.now()
        return bool(self.is_active and self.starts_at <= now <= self.ends_at)

    @classmethod
    def get_live(cls):
        """Queryset of announcements currently visible, highest priority first."""
        now = timezone.now()
        return cls.objects.filter(
            is_active=True, starts_at__lte=now, ends_at__gte=now
        ).order_by("-priority", "-starts_at")
