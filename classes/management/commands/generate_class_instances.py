from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from classes.models import ClassSchedule, ClassInstance


class Command(BaseCommand):
    help = "Generates class instances for the specified number of days ahead and closes out old ones."

    def add_arguments(self, parser):
        parser.add_argument(
            "days",
            type=int,
            nargs="?",
            default=3,
            help="Number of days to generate instances for (default: 3)",
        )

    def handle(self, *args, **options):
        days_ahead = options["days"]
        today = timezone.localdate()

        self.stdout.write(
            self.style.SUCCESS(
                f"Generating class instances for {days_ahead} days ahead..."
            )
        )

        # Mark past instances as COMPLETED
        completed_instances = ClassInstance.objects.filter(
            date__lt=today, status__in=["OPEN", "FULL"]
        )
        completed_count = completed_instances.count()
        for instance in completed_instances:
            instance.status = "COMPLETED"
            instance.save()

        self.stdout.write(
            self.style.WARNING(f"Marked {completed_count} past instances as COMPLETED")
        )

        # Generate instances for the specified number of days
        created_count = 0
        for i in range(days_ahead):
            target_date = today + timedelta(days=i)
            day_of_week = target_date.weekday()

            schedules = ClassSchedule.objects.filter(day_of_week=day_of_week)

            for schedule in schedules:
                instance, created = ClassInstance.objects.get_or_create(
                    class_schedule=schedule,
                    date=target_date,
                    defaults={
                        "start_time": schedule.start_time,
                        "end_time": schedule.end_time,
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        f"Created instance: {schedule.class_obj.name} on {target_date}"
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} new class instances")
        )
        self.stdout.write(
            self.style.SUCCESS("Class instance generation completed successfully")
        )
