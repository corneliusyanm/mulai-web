from django.db import models
from django.utils import timezone

from accounts.models import Member


class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, db_index=True)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-check_in_time"]
        indexes = [
            models.Index(
                fields=["member", "check_in_time"], name="visit_member_checkin_idx"
            ),
            models.Index(fields=["check_in_time"], name="visit_checkin_idx"),
        ]
