from django.db import models
from django.utils import timezone

from accounts.models import Member


class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ("PAYMENT_DUE", "Bayar Cicilan"),
        ("NO_VISIT", "Lama Tidak Visit"),
        ("MEMBERSHIP_EXPIRING", "Membership Berakhir"),
        ("LOKER", "Loker"),
        ("LAINNYA", "Lainnya"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    reason = models.TextField()
    due_date = models.DateField(help_text="The date this reminder is for")
    created_date = models.DateTimeField(default=timezone.now)
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateTimeField(null=True, blank=True)

    def mark_resolved(self):
        """Mark this reminder as resolved"""
        self.is_resolved = True
        self.resolved_date = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_date"])

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Active"
        return f"{self.member.name} - {self.get_reminder_type_display()} - {status}"

    class Meta:
        ordering = ["-created_date"]
        # This will be managed by the new migration
        db_table = "visits_reminder"
