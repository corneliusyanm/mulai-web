from django.db import models
from django.utils import timezone

from accounts.models import Member


class Visit(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-check_in_time"]


class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ("PAYMENT_DUE", "Payment Due (Cicilan)"),
        ("NO_VISIT", "No Visit (2 Weeks)"),
        ("MEMBERSHIP_EXPIRING", "Membership Expiring"),
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
        # Remove unique constraint and rely on logic to prevent duplicates
