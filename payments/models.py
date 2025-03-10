from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, datetime
from accounts.models import Member

class Payment(models.Model):
    DURATION_CHOICES = [
        (1, '1 Day'),
        (30, '1 Month'),
        (90, '3 Months'),
        (180, '6 Months'),
        (365, '12 Months'),
        (0, 'Custom')  # For custom duration input
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=0)  # Changed for Rupiah
    payment_date = models.DateTimeField(default=timezone.now)
    duration_choice = models.IntegerField(choices=DURATION_CHOICES, default=30)
    duration_days = models.IntegerField(help_text="Custom duration in days", null=True, blank=True)
    membership_end_date = models.DateTimeField(editable=False)  # Make it not editable in forms
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_payments'
    )
    
    def save(self, *args, **kwargs):
        # Determine the actual duration days
        actual_duration = self.duration_days if self.duration_choice == 0 else self.duration_choice
        
        # Calculate membership end date based on duration
        if not self.pk or not self.membership_end_date:
            # If member has existing active membership, extend from that date
            try:
                last_payment = Payment.objects.filter(
                    member=self.member,
                    membership_end_date__gt=timezone.now()
                ).latest('membership_end_date')
                start_date = last_payment.membership_end_date.date()
            except Payment.DoesNotExist:
                # Use payment_date or current date if payment_date is not set
                if self.payment_date:
                    start_date = self.payment_date.date()
                else:
                    start_date = timezone.now().date()

            # Set only the date part without time
            end_date = start_date + timedelta(days=actual_duration)
            self.membership_end_date = timezone.make_aware(
                datetime.combine(end_date, datetime.min.time())
            )

        # Update member's active_until field
        if self.member and self.membership_end_date:
            # Only update if the new end date is later than the current active_until
            if not self.member.active_until or self.membership_end_date > self.member.active_until:
                self.member.active_until = self.membership_end_date
                self.member.save(update_fields=['active_until'])

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} - Rp {self.amount:,.0f} - {self.payment_date.strftime('%d %b %Y')}"

    class Meta:
        ordering = ['-payment_date']
