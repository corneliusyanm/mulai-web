"""Create the one PenaltySettings row, starting from the day this is deployed.

`effective_from` is deliberately "now" rather than a hard-coded date: nobody
should be penalised for classes they missed before the rule existed, so the clock
starts when this migration runs on the server. That also means the first possible
penalty is three missed days away, so expect a quiet first week or two.
"""

from django.db import migrations
from django.utils import timezone


def create_settings(apps, schema_editor):
    PenaltySettings = apps.get_model("classes", "PenaltySettings")
    if PenaltySettings.objects.exists():
        return
    PenaltySettings.objects.create(
        enabled=True,
        window_days=15,
        misses_allowed=2,
        ban_days=3,
        effective_from=timezone.localdate(),
    )


def drop_settings(apps, schema_editor):
    PenaltySettings = apps.get_model("classes", "PenaltySettings")
    PenaltySettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("classes", "0003_penaltysettings_bookingpenalty_classmiss_and_more"),
    ]

    operations = [migrations.RunPython(create_settings, drop_settings)]
