from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.dates import day_month, day_month_year
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
                # There is still no way to tell them. The row at least records
                # *when* they got the seat, which is what keeps a late-cancel
                # strike off someone who never knew they had one.
                WaitlistPromotion.objects.update_or_create(
                    member=member_to_move,
                    class_instance=self,
                    defaults={"promoted_at": timezone.now()},
                )
                return True
        return False

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = ("class_schedule", "date")
        indexes = [
            models.Index(fields=["date", "start_time"], name="class_date_time_idx"),
            models.Index(fields=["status"], name="class_status_idx"),
        ]


class WaitlistPromotion(models.Model):
    """When a waitlisted member was moved into a real booking.

    Members have no notification channel, so a promotion that happens an hour
    before a class is a seat handed to somebody who will never look. That is a
    problem we have not solved. What this row does solve is the unfair half of
    it: a member promoted after the cancellation deadline had already passed
    cannot then be struck for cancelling a booking they never asked for.

    `update_or_create`, not `get_or_create`: a member can leave the queue, rejoin
    and be promoted again, and it is the latest promotion that decides.
    """

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="waitlist_promotions"
    )
    class_instance = models.ForeignKey(
        ClassInstance, on_delete=models.CASCADE, related_name="waitlist_promotions"
    )
    promoted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Naik dari Antrian"
        verbose_name_plural = "Naik dari Antrian"
        ordering = ["-promoted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "class_instance"], name="one_promotion_per_booking"
            )
        ]

    def __str__(self):
        return f"{self.member.name} naik dari antrian {self.class_instance}"


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


def class_start_at(instance):
    """The moment the class starts, as an aware Jakarta datetime.

    Every time rule in this file measures from here, so the four hours before a
    class and the hour before a class are always measured the same way. Naive
    date + time is what the model stores; `make_aware` reads TIME_ZONE, which is
    Asia/Jakarta, and that is the clock members are looking at.
    """
    return timezone.make_aware(
        timezone.datetime.combine(instance.date, instance.start_time)
    )


def cancel_deadline_at(instance, settings=None):
    """Last moment a member can cancel this class for free.

    After this, cancelling still works (the seat has to go back somehow) but it
    counts as a miss, exactly like not turning up. Cancelling ten minutes before
    hands the waitlist a seat nobody can act on, which is the same wasted seat as
    a no-show with an extra person disappointed.
    """
    settings = settings or PenaltySettings.get_solo()
    return class_start_at(instance) - timedelta(hours=settings.late_cancel_hours)


def extra_booking_opens_at(instance, settings=None):
    """When a member who already has a class that day may book this one.

    The second class of a day is not something you hold all week: it opens
    shortly before it starts, so the seat spends most of its life available to
    members who have no class that day at all.
    """
    settings = settings or PenaltySettings.get_solo()
    return class_start_at(instance) - timedelta(
        minutes=settings.extra_booking_minutes
    )


def spell_minutes(minutes):
    """"60" as "1 jam", "90" as "90 menit". For copy members have to read fast."""
    if minutes and minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} jam"
    return f"{minutes} menit"


def booking_block_reason(
    member, instance, held_that_day=None, now=None, settings=None
):
    """Why `member` may not book `instance`, or None when they may.

    One place for the booking rules so the class list, the class detail page and
    the book_class POST always agree: a member never sees a button that the
    server then refuses. Being booked or waitlisted already is not handled here,
    those members get a cancel button instead.

    `held_that_day` is how many classes the member already holds on that date.
    Pass it when you already know (the list page counts every date in one query);
    leave it out and it gets counted here. `now` and `settings` are the same
    idea: the class list resolves them once and passes them down, so drawing 12
    cards does not mean 12 reads of the settings row.

    Returns None, or a dict with:
      code    - STARTED / PENALTY / DAY_LIMIT / SEMI_PRIVATE_INACTIVE /
                PEMULA_INACTIVE
      short   - fits on the small disabled button in the class list
      label   - roomier button label, for the class detail page
      message - the full sentence, for messages.error()
    """
    now = now or timezone.now()
    settings = settings or PenaltySettings.get_solo()
    class_name = instance.class_schedule.class_obj.name.lower()
    class_date_start = timezone.make_aware(
        timezone.datetime.combine(instance.date, timezone.datetime.min.time())
    )

    # Before anything about this member: a class that has already started is not
    # bookable by anyone. The list hides those cards, but the detail page and a
    # stale form both reach the POST, and "Kena Penalti" would be the wrong
    # answer to give someone opening yesterday's class.
    if class_start_at(instance) <= now:
        return {
            "code": "STARTED",
            "short": "Sudah Mulai",
            "label": "Kelas Sudah Mulai",
            "message": "Kelas ini sudah mulai, jadi bookingnya sudah ditutup.",
        }

    # Then, because it outranks everything else: while a no-show penalty is
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
                f"{day_month_year(member.booking_blocked_until)} karena beberapa kali "
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

    # The daily limit, and the one rule in here that is about *when* rather than
    # whether. A member already holding a class that day is not refused a second
    # one, they are told to come back shortly before it starts. Until then the
    # seat stays available to members who have no class that day at all, which is
    # the whole point: the evening classes were being held all week by the same
    # faces while people who booked nothing found them full.
    if held_that_day is None:
        held_that_day = member_classes_on_date(member, instance.date).count()
    if held_that_day >= settings.advance_classes_per_day:
        opens_at = timezone.localtime(extra_booking_opens_at(instance, settings))
        if now < opens_at:
            clock = opens_at.strftime("%H:%M")
            return {
                "code": "DAY_LIMIT",
                "short": f"Bisa jam {clock}",
                "label": f"Bisa Booking Jam {clock}",
                "message": (
                    f"Sehari booking {settings.advance_classes_per_day} kelas "
                    f"dulu, biar member lain kebagian tempat. Kelas tambahan di "
                    f"tanggal {day_month_year(instance.date)} bisa dibooking "
                    f"mulai jam {clock}, yaitu "
                    f"{spell_minutes(settings.extra_booking_minutes)} sebelum "
                    f"kelasnya mulai."
                ),
            }

    return None


class GymClosure(models.Model):
    """A day, or a run of days, with no classes. Written before they exist.

    The generator runs three days ahead, so by the time an admin opens /admin and
    sees the instances for a public holiday, members have already booked them and
    somebody has to tell each of those members personally that the class is off.
    A closure written any time in advance stops those instances being created at
    all: there is nothing to book, so there is nothing to apologise for.

    Added late it still helps. Saving one cancels the instances already generated
    inside its range and files a staff reminder for every member who had booked
    one, which is the same work as before except nobody has to find them first.

    `class_obj` empty means the whole gym is shut. Filled in, only that class is
    off, which is what a trainer on leave actually looks like.
    """

    start_date = models.DateField(help_text="Hari pertama kelas ditiadakan.")
    end_date = models.DateField(
        help_text="Hari terakhir kelas ditiadakan. Sama dengan tanggal mulai kalau cuma sehari."
    )
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="closures",
        verbose_name="Kelas",
        help_text="Kosongkan kalau semua kelas ditiadakan. Isi kalau cuma satu kelas yang libur.",
    )
    reason = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Alasan",
        help_text="Dilihat member di halaman jadwal kelas, contoh: Libur Idul Adha.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Libur / Kelas Ditiadakan"
        verbose_name_plural = "Libur / Kelas Ditiadakan"
        ordering = ["start_date", "class_obj__name"]
        indexes = [models.Index(fields=["start_date", "end_date"])]

    def __str__(self):
        what = self.class_obj.name if self.class_obj else "Semua kelas"
        if self.start_date == self.end_date:
            return f"{what} libur {day_month_year(self.start_date)}"
        return (
            f"{what} libur {day_month(self.start_date)} - "
            f"{day_month_year(self.end_date)}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "Tanggal selesai tidak boleh sebelum tanggal mulai."}
            )

    def save(self, *args, **kwargs):
        """Save, then clear out anything already generated inside the range.

        Side effects in save() rather than a signal or an admin hook, because
        /admin is the only place a closure is ever written and a closure that
        does not actually close the classes is worse than none: the admin would
        believe it was handled.
        """
        if not self.end_date:
            self.end_date = self.start_date
        super().save(*args, **kwargs)
        self.cancel_generated_instances()

    def covers(self, date, class_obj_id=None):
        """Whether this closure applies to a class on `date`."""
        if not (self.start_date <= date <= self.end_date):
            return False
        return self.class_obj_id is None or self.class_obj_id == class_obj_id

    def matching_instances(self):
        """Instances already created inside this closure, still live."""
        instances = ClassInstance.objects.filter(
            date__gte=self.start_date, date__lte=self.end_date
        ).exclude(status="CANCELLED")
        if self.class_obj_id:
            instances = instances.filter(
                class_schedule__class_obj_id=self.class_obj_id
            )
        return instances.select_related("class_schedule__class_obj")

    def cancel_generated_instances(self):
        """Cancel what the cron already made, and tell staff who to contact.

        Bookings are left on the cancelled instance on purpose. A CANCELLED class
        stops counting against the member's daily limit and disappears from the
        list on its own, and the rows are the only record of who to apologise to.
        """
        from reminders.models import Reminder

        cancelled = 0
        for instance in self.matching_instances():
            instance.status = "CANCELLED"
            instance.save(update_fields=["status"])
            cancelled += 1
            note = self.reason or "gym libur"
            for member in list(instance.booked_members.all()) + list(
                instance.waitlisted_members.all()
            ):
                Reminder.objects.get_or_create(
                    member=member,
                    reminder_type="KELAS_LIBUR",
                    due_date=instance.date,
                    defaults={
                        "reason": (
                            f"{member.name} udah booking "
                            f"{instance.class_schedule.class_obj.name} "
                            f"{day_month(instance.date)} jam "
                            f"{instance.start_time:%H:%M}, tapi kelasnya "
                            f"ditiadakan ({note}). Kabarin ya."
                        )
                    },
                )
        return cancelled

    @classmethod
    def upcoming(cls, today=None, days=None):
        """Closures that have not finished yet, soonest first.

        `days` trims it to the horizon the class list actually shows, so a
        closure three months out does not sit at the top of the page all quarter.
        """
        today = today or timezone.localdate()
        closures = cls.objects.filter(end_date__gte=today).select_related("class_obj")
        if days is not None:
            closures = closures.filter(start_date__lte=today + timedelta(days=days))
        return closures.order_by("start_date")


class PenaltySettings(models.Model):
    """Every tunable number in the class rules, editable at /admin.

    A settings row rather than module constants, which is the opposite of what
    this project does everywhere else. The reason is that these numbers are being
    tuned by watching real members: the right window, the right number of
    chances, how early a cancellation has to be, how long before a class the
    extra seats open. Each one is an experiment, and a deploy per experiment is
    the wrong shape of friction. If they ever settle, moving them into code is a
    small change.

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
    late_cancel_hours = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(48)],
        help_text=(
            "Batalin kurang dari sekian jam sebelum kelas mulai dihitung sama "
            "kayak nggak dateng. Batalin lebih awal dari itu bebas, nggak ada "
            "catatan apa-apa."
        ),
    )
    advance_classes_per_day = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=(
            "Berapa kelas per hari yang boleh dibooking jauh-jauh hari. "
            "Kelas berikutnya di hari yang sama baru buka menjelang mulai."
        ),
    )
    extra_booking_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(5), MaxValueValidator(1440)],
        help_text=(
            "Kelas ke-2 dan seterusnya di hari yang sama baru bisa dibooking "
            "sekian menit sebelum kelas itu mulai."
        ),
    )
    effective_from = models.DateField(
        help_text=(
            "Kelas sebelum tanggal ini tidak dihitung. Diisi tanggal fitur ini "
            "mulai jalan, biar nggak ada yang kena penalti karena kebiasaan lama."
        )
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Aturan & Penalti Kelas"
        verbose_name_plural = "Aturan & Penalti Kelas"

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
    """One booked class a member did not turn up for, or dropped too late.

    Recorded rather than derived on the fly, for two reasons: the window query
    stays a simple date range, and the history survives a booking being cancelled
    or a class being deleted later.

    Two kinds, counted exactly the same because they cost the same seat. A
    NO_SHOW is written by the nightly command. A LATE_CANCEL is written the
    moment the member cancels inside the deadline, since by then the seat is
    already as good as wasted and there is nothing to wait for.

    Unique per (member, class instance), which is what makes the nightly command
    safe to run twice, and what stops a member who late-cancels and re-books the
    same class collecting two strikes for one seat.
    """

    KIND_CHOICES = [
        ("NO_SHOW", "Nggak dateng"),
        ("LATE_CANCEL", "Batalin mepet"),
    ]

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
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default="NO_SHOW")
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
        return (
            f"{self.member.name} {self.get_kind_display().lower()} "
            f"{self.class_name} {self.class_date}"
        )


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
