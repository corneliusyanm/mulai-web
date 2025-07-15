from django.db import models

# Create your models here.


class GrandOpeningRegistration(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nama")
    phone_number = models.CharField(max_length=20, verbose_name="No. HP")
    age = models.IntegerField(verbose_name="Usia")
    gym_experience = models.CharField(
        max_length=100, verbose_name="Udah pernah rutin nge-Gym atau belum?"
    )
    know_mulai_gym_from = models.CharField(
        max_length=255, verbose_name="Kenal Mulai Gym dari mana?"
    )
    social_media_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Username akun Instagram/TikTok/Facebook (Opsional)",
    )
    visit_schedule = models.CharField(
        max_length=100,
        verbose_name="Mau datang kapan? (mulai dari 19 Juli 10.00 pagi ya!)",
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.visit_schedule}"

    class Meta:
        verbose_name = "Grand Opening Registration"
        verbose_name_plural = "Grand Opening Registrations"
        ordering = ["-created_at"]
