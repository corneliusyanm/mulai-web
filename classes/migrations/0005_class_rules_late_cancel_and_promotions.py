"""The booking rules become time-based, and a wasted seat gets a kind.

`kind` defaults to NO_SHOW, which is what every existing row is: nothing else was
recordable before this. The three new settings fields carry the numbers the rules
were designed around (1 class a day booked ahead, extras from 60 minutes before,
4 hours to cancel for free), and an admin can move any of them without a deploy.
"""

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_member_booking_blocked_until"),
        ("classes", "0004_seed_penalty_settings"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="penaltysettings",
            options={
                "verbose_name": "Aturan & Penalti Kelas",
                "verbose_name_plural": "Aturan & Penalti Kelas",
            },
        ),
        migrations.AddField(
            model_name="classmiss",
            name="kind",
            field=models.CharField(
                choices=[("NO_SHOW", "Nggak dateng"), ("LATE_CANCEL", "Batalin mepet")],
                default="NO_SHOW",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="penaltysettings",
            name="advance_classes_per_day",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text=(
                    "Berapa kelas per hari yang boleh dibooking jauh-jauh hari. "
                    "Kelas berikutnya di hari yang sama baru buka menjelang mulai."
                ),
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
            ),
        ),
        migrations.AddField(
            model_name="penaltysettings",
            name="extra_booking_minutes",
            field=models.PositiveSmallIntegerField(
                default=60,
                help_text=(
                    "Kelas ke-2 dan seterusnya di hari yang sama baru bisa dibooking "
                    "sekian menit sebelum kelas itu mulai."
                ),
                validators=[
                    django.core.validators.MinValueValidator(5),
                    django.core.validators.MaxValueValidator(1440),
                ],
            ),
        ),
        migrations.AddField(
            model_name="penaltysettings",
            name="late_cancel_hours",
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text=(
                    "Batalin kurang dari sekian jam sebelum kelas mulai dihitung sama "
                    "kayak nggak dateng. Batalin lebih awal dari itu bebas, nggak ada "
                    "catatan apa-apa."
                ),
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(48),
                ],
            ),
        ),
        migrations.CreateModel(
            name="WaitlistPromotion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("promoted_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "class_instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="waitlist_promotions",
                        to="classes.classinstance",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="waitlist_promotions",
                        to="accounts.member",
                    ),
                ),
            ],
            options={
                "verbose_name": "Naik dari Antrian",
                "verbose_name_plural": "Naik dari Antrian",
                "ordering": ["-promoted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="waitlistpromotion",
            constraint=models.UniqueConstraint(
                fields=("member", "class_instance"), name="one_promotion_per_booking"
            ),
        ),
    ]
