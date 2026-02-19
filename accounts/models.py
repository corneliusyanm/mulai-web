import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("admin", "Admin"),
        ("superadmin", "Super Admin"),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)

    # Member-specific fields
    age = models.IntegerField(null=True, blank=True)
    height = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )  # in cm
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )  # in kg
    years_of_working_out = models.IntegerField(null=True, blank=True)
    active_until = models.DateTimeField(null=True, blank=True)

    def is_superadmin(self):
        return self.user_type == "superadmin"

    def is_admin(self):
        return self.user_type == "admin"

    @property
    def is_active_member(self):
        if not self.active_until:
            return False
        # Consider active if end date is today or in the future
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.active_until >= today_start


class Member(models.Model):
    GENDER_CHOICES = (
        ("F", "Perempuan"),
        ("M", "Laki-laki"),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.IntegerField()
    height = models.DecimalField(max_digits=5, decimal_places=2)  # in cm
    weight = models.DecimalField(max_digits=5, decimal_places=2)  # in kg
    address = models.TextField(blank=True, default="")
    social_media_username = models.CharField(
        "(Opsional) Akun Instagram/TikTok", max_length=255, blank=True, default=""
    )
    years_of_working_out = models.CharField(max_length=100)
    goals = models.TextField()
    know_mulai_gym_from = models.CharField(max_length=255)
    why_choose_mulai = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    active_until = models.DateTimeField(null=True, blank=True)
    pemula_active_until = models.DateTimeField(null=True, blank=True)
    semi_private_active_until = models.DateTimeField(null=True, blank=True)
    pt_session_count = models.IntegerField(
        default=0, help_text="Jumlah sesi personal training yang tersisa"
    )
    is_pemula = models.BooleanField(
        null=True,
        blank=True,
        help_text="Status pemula member - bisa true, false, atau kosong",
    )

    notes = models.TextField(
        blank=True,
        default="",
        help_text="Catatan internal admin saja, tidak ditampilkan ke member",
    )

    # Admin tracking flags
    asked_referral = models.BooleanField(
        default=False,
        help_text="Flag: sudah ditanya apakah punya kenalan yang bisa diajak ke gym",
    )
    asked_google_review = models.BooleanField(
        default=False,
        help_text="Flag: sudah diminta untuk memberikan Google review",
    )
    missed_installment = models.BooleanField(
        default=False,
        help_text="Flag: member yang cicilan tapi tidak melanjutkan pembayaran",
    )
    skip_auto_reminder = models.BooleanField(
        default=False,
        help_text="Flag: jangan buat reminder otomatis untuk member ini",
    )

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_active_member(self):
        if not self.active_until:
            return False
        # Consider active if end date is today or in the future
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.active_until >= today_start

    @property
    def is_pemula_active_member(self):
        if not self.pemula_active_until:
            return False
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.pemula_active_until >= today_start

    @property
    def is_semi_private_active_member(self):
        if not self.semi_private_active_until:
            return False
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.semi_private_active_until >= today_start

    @property
    def is_pt_active_member(self):
        if not self.pt_session_count:
            return False
        return self.pt_session_count > 0

    class Meta:
        ordering = ["-created_at"]


class ActiveMember(Member):
    """Proxy model for viewing only active members in admin"""

    class Meta:
        proxy = True
        verbose_name = "Active Member"
        verbose_name_plural = "Active Members"


class Tamu(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nama")
    phone_number = models.CharField(max_length=20, verbose_name="No. HP")
    has_worked_out_before = models.CharField(
        max_length=100,
        verbose_name="Sudah pernah rutin nge-Gym? Kalau sudah, berapa lama?",
    )
    social_media_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Username akun Instagram/TikTok/Facebook",
    )
    is_pemula = models.BooleanField(
        null=True,
        blank=True,
        help_text="Status pemula tamu - bisa true, false, atau null",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tamu"
        verbose_name_plural = "Tamu"
        ordering = ["-created_at"]


class Masukkan(models.Model):
    name = models.CharField(max_length=100, blank=True, verbose_name="Nama")
    contact = models.CharField(
        max_length=100, blank=True, verbose_name="Kontak (no WA / sosial media)"
    )
    feedback = models.TextField(verbose_name="Masukkan")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.name or 'Anonymous'} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Masukkan"
        verbose_name_plural = "Masukkan"
        ordering = ["-created_at"]


class Prospect(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nama")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="No. HP")
    gym_experience = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="(Opsional) Udah pernah rutin nge-Gym atau belum?",
    )
    social_media_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="(Opsional) Username ig/fb/tiktok",
    )
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Disubmit oleh",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Prospek"
        verbose_name_plural = "Prospek"
        ordering = ["-created_at"]
