from django.db import migrations

# From the Google Maps listing on 2026-08-01. Editable in the admin afterwards,
# so this only ever has to be right on the day it ships.
MAPS_URL = "https://maps.app.goo.gl/gxB7Y52aXgERXkby7"
RATING = "5.0"
REVIEW_COUNT = 142


def seed(apps, schema_editor):
    ReviewSummary = apps.get_model("homepage", "ReviewSummary")
    if ReviewSummary.objects.exists():
        return
    ReviewSummary.objects.create(
        rating=RATING,
        review_count=REVIEW_COUNT,
        maps_url=MAPS_URL,
    )


def unseed(apps, schema_editor):
    ReviewSummary = apps.get_model("homepage", "ReviewSummary")
    ReviewSummary.objects.filter(maps_url=MAPS_URL).delete()


class Migration(migrations.Migration):
    dependencies = [("homepage", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
