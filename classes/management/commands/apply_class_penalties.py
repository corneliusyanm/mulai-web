"""Record the day's no-shows and lock booking for anyone over the allowance.

Runs after the gym closes, when every class that day is settled. See
classes/penalties.py for the rules and why they are shaped that way.

    python manage.py apply_class_penalties               # tonight
    python manage.py apply_class_penalties --dry-run     # show, change nothing
    python manage.py apply_class_penalties --date 2026-08-15   # catch up a day
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from classes.penalties import apply_penalties


class Command(BaseCommand):
    help = "Record class no-shows for a day and apply booking penalties"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Day to process as YYYY-MM-DD. Defaults to today (Asia/Jakarta).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would happen and roll it back.",
        )

    def handle(self, *args, **options):
        day = timezone.localdate()
        if options.get("date"):
            try:
                day = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("--date must look like 2026-08-15")

        dry_run = bool(options.get("dry_run"))
        self.stdout.write(
            f"Checking class no-shows for {day}" + (" (dry run)" if dry_run else "")
        )

        report = apply_penalties(day=day, dry_run=dry_run)
        settings_row = report["settings"]

        if not report["enabled"]:
            self.stdout.write(
                self.style.WARNING("Penalties are switched off in /admin, nothing done")
            )
            return
        if report["before_effective_from"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{day} is before the start date {settings_row.effective_from}, "
                    "nothing done"
                )
            )
            return

        self.stdout.write(
            f"Rule: {settings_row.misses_allowed} misses allowed per "
            f"{settings_row.window_days} days, then {settings_row.ban_days} days locked"
        )
        self.stdout.write(f"New no-shows recorded: {report['misses_recorded']}")

        for penalty in report["penalties"]:
            self.stdout.write(
                self.style.WARNING(
                    f"  {penalty.member.name}: {penalty.miss_days} missed days, "
                    f"booking locked until {penalty.blocked_until}, "
                    f"{penalty.bookings_cancelled} bookings cancelled, "
                    f"{penalty.waitlists_cleared} waitlist places dropped"
                )
            )

        if report["skipped_existing"]:
            self.stdout.write(
                f"Already penalised today, left alone: {report['skipped_existing']}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(report['penalties'])} penalties "
                + ("would be applied" if dry_run else "applied")
            )
        )
