import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
