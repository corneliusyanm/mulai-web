from django.db import migrations
from datetime import timedelta

def calculate_duration_days(apps, schema_editor):
    Payment = apps.get_model('payments', 'Payment')
    for payment in Payment.objects.all():
        # Calculate days between payment date and membership end date
        delta = payment.membership_end_date - payment.payment_date
        payment.duration_days = delta.days
        payment.save()

class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_remove_payment_duration_months_payment_duration_days_and_more'),  # Your existing 0004 migration
    ]

    operations = [
        migrations.RunPython(calculate_duration_days),
    ] 