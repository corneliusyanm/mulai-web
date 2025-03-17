from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Member


class Payment(models.Model):
    DURATION_CHOICES = [
        (1, "1 Day"),
        (30, "1 Month"),
        (90, "3 Months"),
        (180, "6 Months"),
        (365, "12 Months"),
        (0, "Custom"),  # For custom duration input
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_payments",
    )

    def save(self, *args, **kwargs):
        # Calculate membership end date based on duration
        if not self.pk or not self.membership_end_date:
            # Determine start date
            # If member has existing active membership, extend from that date
            try:
                last_payment = Payment.objects.filter(
                    member=self.member,
                    membership_end_date__gte=timezone.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                ).latest("membership_end_date")
                start_date = last_payment.membership_end_date.date()
            except Payment.DoesNotExist:
                # Use payment_date or current date if payment_date is not set
                if self.payment_date:
                    start_date = self.payment_date.date()
                else:
                    start_date = timezone.now().date()

            # Calculate end date based on duration choice
            if self.duration_choice == 1:  # 1 Day
                # End of current day (23:59:59)
                end_date = start_date
                end_time = datetime.max.time()  # 23:59:59.999999
            elif self.duration_choice == 30:  # 1 Month
                # Same day next month (or last day if that day doesn't exist)
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
                end_time = datetime.max.time()
            elif self.duration_choice == 90:  # 3 Months
                end_date = start_date + relativedelta(months=3) - timedelta(days=1)
                end_time = datetime.max.time()
            elif self.duration_choice == 180:  # 6 Months
                end_date = start_date + relativedelta(months=6) - timedelta(days=1)
                end_time = datetime.max.time()
            elif self.duration_choice == 365:  # 12 Months
                end_date = start_date + relativedelta(months=12) - timedelta(days=1)
                end_time = datetime.max.time()
            elif self.duration_choice == 0 and self.duration_days:  # Custom
                # Inclusive of end date
                end_date = start_date + timedelta(days=self.duration_days - 1)
                end_time = datetime.max.time()
            else:
                # Default fallback
                end_date = start_date
                end_time = datetime.max.time()

            # Set the membership end date with the end of the day time
            self.membership_end_date = timezone.make_aware(
                datetime.combine(end_date, end_time)
            )

        # Update member's active_until field
        if self.member and self.membership_end_date:
            # Only update if the new end date is later than the current
            # active_until
            if (
                not self.member.active_until
                or self.membership_end_date > self.member.active_until
            ):
                self.member.active_until = self.membership_end_date
                self.member.save(update_fields=["active_until"])

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} - Rp {self.amount:,.0f} - {self.payment_date.strftime('%d %b %Y')}"

    class Meta:
        ordering = ["-payment_date"]
