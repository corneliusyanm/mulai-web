from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from accounts.models import Member

class Payment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=0)  # Changed for Rupiah
    payment_date = models.DateTimeField(default=timezone.now)
    duration_days = models.IntegerField(help_text="Duration in days", null=True, blank=True)  # Make it nullable temporarily
    membership_end_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_payments'
    )
    
    def save(self, *args, **kwargs):
        # Calculate membership end date based on duration
        if not self.membership_end_date:
            # If member has existing active membership, extend from that date
            try:
                last_payment = Payment.objects.filter(
                    member=self.member,
                    membership_end_date__gt=timezone.now()
                ).latest('membership_end_date')
                start_date = last_payment.membership_end_date
            except Payment.DoesNotExist:
                start_date = timezone.now()

            self.membership_end_date = start_date + timedelta(days=self.duration_days)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} - Rp {self.amount:,.0f} - {self.payment_date.strftime('%d %b %Y')}"

    class Meta:
        ordering = ['-payment_date']
