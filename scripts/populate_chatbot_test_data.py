"""
Script to populate local database with test class data for chatbot testing.
Run with: python manage.py shell < scripts/populate_chatbot_test_data.py
"""

from datetime import date, time, timedelta
from django.utils import timezone
from classes.models import Class, ClassSchedule, ClassInstance

print("🏋️ Populating class data for chatbot testing...")

# Create or get Class types
classes_data = [
    {
        "name": "Semi Private",
        "description": "Semi-private training session, max 4 people",
        "max_members": 4,
    },
    {
        "name": "Kelas Pemula (Push)",
        "description": "Beginner class focusing on push exercises",
        "max_members": 6,
    },
    {
        "name": "Kelas Pemula (Pull)",
        "description": "Beginner class focusing on pull exercises",
        "max_members": 6,
    },
    {
        "name": "Kelas Pemula (Leg & Core)",
        "description": "Beginner class for legs and core",
        "max_members": 6,
    },
]

class_objs = {}
for cd in classes_data:
    obj, created = Class.objects.get_or_create(
        name=cd["name"],
        defaults={"description": cd["description"], "max_members": cd["max_members"]},
    )
    class_objs[cd["name"]] = obj
    print(f"  {'Created' if created else 'Found'}: {obj.name}")

# Create ClassSchedules
# Semi Private: every day at 07:00, 09:00, 16:15, 19:00
semi_private = class_objs["Semi Private"]
semi_times = [
    (time(7, 0), time(8, 0)),
    (time(9, 0), time(10, 0)),
    (time(16, 15), time(17, 15)),
    (time(19, 0), time(20, 0)),
]

for day in range(7):  # 0=Monday to 6=Sunday
    for start, end in semi_times:
        schedule, created = ClassSchedule.objects.get_or_create(
            class_obj=semi_private,
            day_of_week=day,
            start_time=start,
            defaults={"end_time": end},
        )

print(f"  Created Semi Private schedules")

# Pemula schedules
pemula_times = [
    (time(8, 0), time(8, 45)),
    (time(15, 30), time(16, 15)),
    (time(17, 15), time(18, 0)),
    (time(18, 15), time(19, 0)),
]

pemula_schedule = {
    0: "Kelas Pemula (Push)",  # Monday
    1: "Kelas Pemula (Pull)",  # Tuesday
    2: "Kelas Pemula (Leg & Core)",  # Wednesday
    3: "Kelas Pemula (Push)",  # Thursday
    4: "Kelas Pemula (Pull)",  # Friday
    5: "Kelas Pemula (Leg & Core)",  # Saturday
    # Sunday: no Pemula
}

for day, class_name in pemula_schedule.items():
    class_obj = class_objs[class_name]
    for start, end in pemula_times:
        schedule, created = ClassSchedule.objects.get_or_create(
            class_obj=class_obj,
            day_of_week=day,
            start_time=start,
            defaults={"end_time": end},
        )

print(f"  Created Pemula schedules")

# Create ClassInstances for the next 3 days
today = date.today()
instances_created = 0

for day_offset in range(3):
    target_date = today + timedelta(days=day_offset)
    day_of_week = target_date.weekday()

    # Get all schedules for this day
    schedules = ClassSchedule.objects.filter(day_of_week=day_of_week)

    for schedule in schedules:
        instance, created = ClassInstance.objects.get_or_create(
            class_schedule=schedule,
            date=target_date,
            defaults={
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "status": "OPEN",
            },
        )
        if created:
            instances_created += 1

            # Make 16:15 Semi Private slots FULL for testing
            if (
                schedule.class_obj.name == "Semi Private"
                and schedule.start_time == time(16, 15)
            ):
                instance.status = "FULL"
                instance.save()

print(f"  Created {instances_created} class instances")
print(f"\n✅ Done! You now have class data for {today} to {today + timedelta(days=2)}")
print(
    f"\nTotal classes: {ClassInstance.objects.filter(date__gte=today, status__in=['OPEN', 'FULL']).count()}"
)
