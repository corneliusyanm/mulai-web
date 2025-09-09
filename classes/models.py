from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.models import Member


class Class(models.Model):
    """
    Represents a type of class offered at the gym, e.g., "Yoga", "Zumba".
    """

    name = models.CharField(max_length=100)
    description = models.TextField()
    max_members = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Classes"
        ordering = ["name"]


class ClassSchedule(models.Model):
    """
    Defines the recurring schedule for a class.
    """

    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="schedules"
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.class_obj.name} on {self.get_day_of_week_display()} at {self.start_time.strftime('%H:%M')}"

    class Meta:
        ordering = ["day_of_week", "start_time"]
        unique_together = ("class_obj", "day_of_week", "start_time")


class ClassInstance(models.Model):
    """
    Represents a specific instance of a class that members can book.
    """

    STATUS_CHOICES = [
        ("OPEN", "Open for Booking"),
        ("FULL", "Full"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    class_schedule = models.ForeignKey(
        ClassSchedule, on_delete=models.CASCADE, related_name="instances"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    booked_members = models.ManyToManyField(
        Member, related_name="booked_classes", blank=True
    )
    waitlisted_members = models.ManyToManyField(
        Member, related_name="waitlisted_classes", blank=True
    )

    def __str__(self):
        return f"{self.class_schedule.class_obj.name} on {self.date.strftime('%Y-%m-%d')} at {self.start_time.strftime('%H:%M')}"

    @property
    def is_bookable(self):
        return self.status in ["OPEN", "FULL"] and self.date >= timezone.now().date()

    @property
    def available_slots(self):
        return self.class_schedule.class_obj.max_members - self.booked_members.count()

    def update_status(self):
        """
        Updates the status of the class instance based on the number of booked members.
        """
        if self.booked_members.count() >= self.class_schedule.class_obj.max_members:
            self.status = "FULL"
        else:
            self.status = "OPEN"
        self.save()

    def move_from_waitlist(self):
        if (
            self.waitlisted_members.exists()
            and self.booked_members.count() < self.class_schedule.class_obj.max_members
        ):
            # Get the through model entry for the first person on the waitlist, effectively a FIFO queue
            through_model = self.waitlisted_members.through
            waitlist_entry = (
                through_model.objects.filter(classinstance=self).order_by("id").first()
            )

            if waitlist_entry:
                member_to_move = waitlist_entry.member
                self.waitlisted_members.remove(member_to_move)
                self.booked_members.add(member_to_move)
                self.update_status()
                # Optionally, you could send a notification to the member here
                return True
        return False

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = ("class_schedule", "date")
        indexes = [
            models.Index(fields=["date", "start_time"], name="class_date_time_idx"),
            models.Index(fields=["status"], name="class_status_idx"),
        ]
