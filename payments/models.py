from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Member


class Package(models.Model):
    code = models.CharField(max_length=20, unique=True)
    default_price = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.code} - Rp {self.default_price:,.0f} ({self.description})"

    class Meta:
        ordering = ["code"]


class Payment(models.Model):
    DURATION_CHOICES = [
        (1, "1 Day"),
        (30, "1 Month"),
        (90, "3 Months"),
        (180, "6 Months"),
        (365, "12 Months"),
        (0, "Custom"),  # For custom duration input
    ]

    PAYMENT_METHOD_CHOICES = [
        ("TRANSFER", "Transfer"),
        ("QRIS", "QRIS"),
        ("CASH", "Cash"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=0)  # Changed for Rupiah
    payment_date = models.DateTimeField(default=timezone.now)
    duration_choice = models.IntegerField(choices=DURATION_CHOICES, default=30)
    duration_days = models.IntegerField(
        help_text="Custom duration in days", null=True, blank=True
    )
    membership_end_date = models.DateTimeField(
        editable=False
    )  # Make it not editable in forms
    notes = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default="TRANSFER",
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payments",
    )
    apakah_nyicil = models.BooleanField(default=False, help_text="Apakah cicilan?")

    def save(self, *args, **kwargs):
        # Only calculate membership end date for new payments or if explicitly needed
        calculate_end_date = not self.pk or not self.membership_end_date

        if calculate_end_date:
            today = timezone.now().date()
            start_date = None

            # Determine start date based on member's current status
            if self.member.active_until and self.member.active_until.date() >= today:
                # Member is active, start new period after current one ends
                start_date = self.member.active_until.date() + timedelta(days=1)
            else:
                # Member is inactive or has no active_until, start from payment date
                start_date = self.payment_date.date() if self.payment_date else today

            # Calculate end date based on duration choice and start_date
            end_date = start_date
            end_time = datetime.max.time()  # Default to end of day

            if self.duration_choice == 1:  # 1 Day
                # Ends on the same day it starts
                end_date = start_date
            elif self.duration_choice == 30:  # 1 Month
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
            elif self.duration_choice == 90:  # 3 Months
                end_date = start_date + relativedelta(months=3) - timedelta(days=1)
            elif self.duration_choice == 180:  # 6 Months
                end_date = start_date + relativedelta(months=6) - timedelta(days=1)
            elif self.duration_choice == 365:  # 12 Months
                end_date = start_date + relativedelta(months=12) - timedelta(days=1)
            elif self.duration_choice == 0 and self.duration_days:  # Custom
                # Inclusive of end date
                end_date = start_date + timedelta(days=self.duration_days - 1)
            else:
                # Default fallback (e.g., if duration choice invalid)
                end_date = start_date

            # Set the membership end date with the end of the day time
            self.membership_end_date = timezone.make_aware(
                datetime.combine(end_date, end_time)
            )

        # Call the original save method first to ensure the payment has an ID if new
        super().save(*args, **kwargs)

        # Always update member's active_until field to the new payment's end date
        if self.member and self.membership_end_date:
            self.member.active_until = self.membership_end_date
            self.member.save(update_fields=["active_until"])

    def __str__(self):
        return f"{self.member.name} - Rp {self.amount:,.0f} - {self.payment_date.strftime('%d %b %Y')}"

    class Meta:
        ordering = ["-payment_date"]
