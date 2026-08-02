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
      code    - PENALTY / DAY_LIMIT / SEMI_PRIVATE_INACTIVE / PEMULA_INACTIVE
      short   - fits on the small disabled button in the class list
      label   - roomier button label, for the class detail page
      message - the full sentence, for messages.error()
    """
    class_name = instance.class_schedule.class_obj.name.lower()
    class_date_start = timezone.make_aware(
        timezone.datetime.combine(instance.date, timezone.datetime.min.time())
    )

    # First, because it outranks everything else: while a no-show penalty is
    # running there is no class this member may book, whatever its date. Reads a
    # field already on the member, so it costs the list page nothing. Admins book
    # through /admin, which does not come through here.
    if member.booking_locked():
        return {
            "code": "PENALTY",
            "short": "Kena Penalti",
            "label": "Booking Kelas Dikunci",
            "message": (
                "Booking kelas kamu dikunci sampai "
                f"{member.booking_blocked_until:%d %b %Y} karena beberapa kali "
                "nggak dateng padahal udah booking. Cek halaman Akun Saya buat "
                "detailnya."
            ),
        }

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


class PenaltySettings(models.Model):
    """The no-show penalty rules, editable at /admin.

    A settings row rather than module constants, which is the opposite of what
    this project does everywhere else (see MAX_CLASSES_PER_DAY above). The reason
    is that these three numbers are being tuned by watching real members: the
    right window and the right number of chances are an experiment, and a deploy
    per experiment is the wrong shape of friction. If they ever settle, moving
    them into code is a small change.

    `effective_from` exists so nobody is punished for behaviour from before the
    rule existed. It is set to the day the feature was deployed, and misses on
    earlier class dates are ignored even if they are inside the window.
    """

    enabled = models.BooleanField(
        default=True,
        help_text="Matikan ini untuk menghentikan semua penalti tanpa mengubah data.",
    )
    window_days = models.PositiveSmallIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Berapa hari ke belakang yang dihitung.",
    )
    misses_allowed = models.PositiveSmallIntegerField(
        default=2,
        validators=[MaxValueValidator(50)],
        help_text=(
            "Berapa kali boleh nggak dateng dalam periode itu sebelum kena "
            "penalti. 2 berarti penalti mulai dari kali ke-3."
        ),
    )
    ban_days = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text="Berapa hari booking kelas dikunci tiap kali kena penalti.",
    )
    effective_from = models.DateField(
        help_text=(
            "Kelas sebelum tanggal ini tidak dihitung. Diisi tanggal fitur ini "
            "mulai jalan, biar nggak ada yang kena penalti karena kebiasaan lama."
        )
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pengaturan Penalti Kelas"
        verbose_name_plural = "Pengaturan Penalti Kelas"

    def __str__(self):
        state = "aktif" if self.enabled else "mati"
        return (
            f"Penalti {state}: {self.misses_allowed} kali boleh dalam "
            f"{self.window_days} hari, kunci {self.ban_days} hari"
        )

    @classmethod
    def get_solo(cls):
        """The one row, created with defaults if it somehow is not there.

        The initial migration writes it, so this only has to cope with a fresh
        database or someone deleting the row from /admin.
        """
        settings_row = cls.objects.first()
        if settings_row:
            return settings_row
        return cls.objects.create(effective_from=timezone.localdate())


class ClassMiss(models.Model):
    """One booked class a member did not turn up for.

    Recorded by the nightly command rather than derived on the fly, for two
    reasons: the window query stays a simple date range, and the history survives
    a booking being cancelled or a class being deleted later.

    Unique per (member, class instance), which is what makes the command safe to
    run twice.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="class_misses"
    )
    class_instance = models.ForeignKey(
        ClassInstance, on_delete=models.CASCADE, related_name="misses"
    )
    # Denormalised from the instance so a window is one indexed range scan, and
    # so the date is still here if the instance is ever deleted.
    class_date = models.DateField()
    class_name = models.CharField(max_length=100, blank=True)
    class_start_time = models.TimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kelas Bolos"
        verbose_name_plural = "Kelas Bolos"
        ordering = ["-class_date", "-class_start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "class_instance"], name="one_miss_per_booking"
            )
        ]
        indexes = [models.Index(fields=["member", "class_date"])]

    def __str__(self):
        return f"{self.member.name} bolos {self.class_name} {self.class_date}"


class BookingPenalty(models.Model):
    """A stretch of days where a member may not book classes.

    `blocked_until` is **exclusive**: a 3-day penalty starting on the 15th sets
    it to the 18th, and the 18th is the first day they can book again. The member
    field `Member.booking_blocked_until` uses the same convention, and the UI
    always shows the day they get booking back, since that is the date they
    actually care about.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="booking_penalties"
    )
    starts_on = models.DateField()
    blocked_until = models.DateField(
        help_text="Hari pertama member bisa booking lagi (tanggal ini sudah boleh)."
    )
    miss_days = models.PositiveSmallIntegerField(
        help_text="Berapa hari bolos dalam periode saat penalti ini dibuat."
    )
    bookings_cancelled = models.PositiveSmallIntegerField(default=0)
    waitlists_cleared = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Penalti Kelas"
        verbose_name_plural = "Penalti Kelas"
        ordering = ["-starts_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "starts_on"], name="one_penalty_per_member_per_day"
            )
        ]

    def __str__(self):
        return f"{self.member.name} dikunci {self.starts_on} sampai {self.blocked_until}"

    def is_active(self, today=None):
        today = today or timezone.localdate()
        return self.starts_on <= today < self.blocked_until
