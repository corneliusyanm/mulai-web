"""Days an admin can mark off before the cron has made anything to cancel."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classes", "0005_class_rules_late_cancel_and_promotions"),
    ]

    operations = [
        migrations.CreateModel(
            name="GymClosure",
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
                (
                    "start_date",
                    models.DateField(help_text="Hari pertama kelas ditiadakan."),
                ),
                (
                    "end_date",
                    models.DateField(
                        help_text=(
                            "Hari terakhir kelas ditiadakan. Sama dengan tanggal mulai "
                            "kalau cuma sehari."
                        )
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Dilihat member di halaman jadwal kelas, contoh: "
                            "Libur Idul Adha."
                        ),
                        max_length=120,
                        verbose_name="Alasan",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "class_obj",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "Kosongkan kalau semua kelas ditiadakan. Isi kalau cuma "
                            "satu kelas yang libur."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="closures",
                        to="classes.class",
                        verbose_name="Kelas",
                    ),
                ),
            ],
            options={
                "verbose_name": "Libur / Kelas Ditiadakan",
                "verbose_name_plural": "Libur / Kelas Ditiadakan",
                "ordering": ["start_date", "class_obj__name"],
            },
        ),
        migrations.AddIndex(
            model_name="gymclosure",
            index=models.Index(
                fields=["start_date", "end_date"], name="classes_gym_start_d_0175e7_idx"
            ),
        ),
    ]
