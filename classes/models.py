from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.models import Member

# How many classes one member may hold per day. Members used to book 3-4 classes
# a day just so they would never hit a "full" class, then skip most of them,
# which locked everyone else out. Admins can still go over this from /admin.
MAX_CLASSES_PER_DAY = 2


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
        return self.status in ["OPEN", "FULL"] and self.date >= timezone.localdate()

    @property
    def available_slots(self):
        return self.class_schedule.class_obj.max_members - self.booked_members.count()

    def update_status(self):
        """
        Updates the status of the class instance based on the number of booked members.
        """
        # Never resurrect an instance an admin cancelled, or one already completed.
        # Booking/cancellation activity from still-booked members must not flip
        # a CANCELLED class back to OPEN.
        if self.status in ("CANCELLED", "COMPLETED"):
            return
        if self.booked_members.count() >= self.class_schedule.class_obj.max_members:
            self.status = "FULL"
        else:
            self.status = "OPEN"
        self.save()

    def waitlist_position(self, member):
        """Member's 1-based place in the waitlist, or None if not waitlisted.

        Same FIFO order move_from_waitlist() promotes in, so what a member is
        told matches who actually gets the next free spot.
        """
        through = self.waitlisted_members.through
        queue = list(
            through.objects.filter(classinstance=self)
            .order_by("id")
            .values_list("member_id", flat=True)
        )
        if member.id in queue:
            return queue.index(member.id) + 1
        return None

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


def member_classes_on_dates(member, dates):
    """Classes on `dates` the member holds a spot in, booked or waitlisted.

    Waitlist spots count against the daily limit: they turn into real bookings
    as soon as somebody cancels, so leaving them out would let a member hold
    2 bookings plus a stack of waitlist spots and still end up with 4 classes.

    Classes the gym cancelled are not counted, they never happened.
    """
    return (
        ClassInstance.objects.filter(date__in=dates)
        .exclude(status="CANCELLED")
        .filter(Q(booked_members=member) | Q(waitlisted_members=member))
        .select_related("class_schedule__class_obj")
        .order_by("date", "start_time")
        .distinct()
    )


def member_classes_on_date(member, date):
    """Classes on one date the member holds a spot in. See member_classes_on_dates."""
    return member_classes_on_dates(member, [date])


def booking_block_reason(member, instance, held_that_day=None):
    """Why `member` may not book `instance`, or None when they may.

    One place for the booking rules so the class list, the class detail page and
    the book_class POST always agree: a member never sees a button that the
    server then refuses. Being booked or waitlisted already is not handled here,
    those members get a cancel button instead.

    `held_that_day` is how many classes the member already holds on that date.
    Pass it when you already know (the list page counts every date in one query);
    leave it out and it gets counted here.

    Returns None, or a dict with:
      code    - DAY_LIMIT / SEMI_PRIVATE_INACTIVE / PEMULA_INACTIVE
      short   - fits on the small disabled button in the class list
      label   - roomier button label, for the class detail page
      message - the full sentence, for messages.error()
    """
    class_name = instance.class_schedule.class_obj.name.lower()
    class_date_start = timezone.make_aware(
        timezone.datetime.combine(instance.date, timezone.datetime.min.time())
    )

    if "semi private" in class_name and (
        not member.semi_private_active_until
        or member.semi_private_active_until < class_date_start
    ):
        return {
            "code": "SEMI_PRIVATE_INACTIVE",
            "short": "Gold Tidak Aktif",
            "label": "Membership Gold Tidak Aktif",
            "message": (
                "Membership Gold kamu sudah tidak aktif pada tanggal tersebut. "
                "Silahkan hubungi admin untuk mengaktifkannya."
            ),
        }

    if "kelas pemula" in class_name and (
        not member.pemula_active_until or member.pemula_active_until < class_date_start
    ):
        return {
            "code": "PEMULA_INACTIVE",
            "short": "Silver Tidak Aktif",
            "label": "Membership Silver Tidak Aktif",
            "message": (
                "Membership Silver kamu sudah tidak aktif pada tanggal tersebut. "
                "Silahkan hubungi admin untuk mengaktifkannya."
            ),
        }

    if held_that_day is None:
        held_that_day = member_classes_on_date(member, instance.date).count()
    if held_that_day >= MAX_CLASSES_PER_DAY:
        return {
            "code": "DAY_LIMIT",
            "short": f"Maks {MAX_CLASSES_PER_DAY}/hari",
            "label": f"Maks {MAX_CLASSES_PER_DAY} Kelas per Hari",
            "message": (
                f"Kamu sudah punya {MAX_CLASSES_PER_DAY} kelas di tanggal "
                f"{instance.date.strftime('%d %b %Y')}. Maksimal "
                f"{MAX_CLASSES_PER_DAY} kelas per hari, jadi batalkan salah satu "
                f"dulu kalau mau pindah ke kelas ini."
            ),
        }

    return None
