from collections import defaultdict
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.db import transaction
from django.db.models import Count, Q

from accounts.views import MemberRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from .calendar_export import class_instance_to_ics, ics_filename
from .sharing import whatsapp_invite_url
from .models import (
    ClassInstance,
    Member,
    PenaltySettings,
    booking_block_reason,
    cancel_deadline_at,
    class_start_at,
    member_classes_on_date,
    member_classes_on_dates,
    spell_minutes,
)
from .penalties import member_state, record_late_cancel


def member_login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if "member_email" not in request.session:
            return redirect("member_login")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# Create your views here.


def _attach_cancel_window(instance, now, settings):
    """Put the free-cancellation deadline on an instance, for the templates.

    A clock time, not a countdown: "batalin sebelum jam 13:15" is something a
    member can act on without doing arithmetic, and most of them will not do the
    arithmetic. Localised here rather than in the template because the `time`
    filter formats whatever timezone the datetime carries.
    """
    deadline = cancel_deadline_at(instance, settings)
    instance.cancel_deadline_at = timezone.localtime(deadline)
    instance.cancel_is_late = now >= deadline
    instance.has_started = class_start_at(instance) <= now
    return instance


class ClassListView(MemberRequiredMixin, ListView):
    model = ClassInstance
    template_name = "classes/class_list.html"
    context_object_name = "class_instances"

    def get_queryset(self):
        from datetime import datetime

        now = timezone.now()

        # Get all OPEN/FULL instances first, then filter in Python for precise datetime comparison
        all_instances = (
            ClassInstance.objects.filter(status__in=["OPEN", "FULL"])
            .select_related("class_schedule__class_obj")
            .prefetch_related("booked_members")
            .annotate(booked_count=Count("booked_members", distinct=True))
            .order_by("date", "start_time")
        )

        upcoming_instances = []
        for instance in all_instances:
            # Combine date and start_time into a timezone-aware datetime
            class_dt = timezone.make_aware(
                datetime.combine(instance.date, instance.start_time)
            )

            if class_dt > now:
                upcoming_instances.append(instance)

        return upcoming_instances

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instances = context["class_instances"]
        member = None
        member_email = self.request.session.get("member_email")
        if member_email:
            member = Member.objects.filter(email=member_email).first()
        context["member"] = member

        # One read of the rules for the whole page. Every card needs the same
        # numbers, and booking_block_reason() would otherwise fetch the row again
        # per card, which is exactly the per-card query this view exists to avoid.
        now = timezone.now()
        settings = PenaltySettings.get_solo()
        context["rules"] = settings
        context["advance_classes_per_day"] = settings.advance_classes_per_day
        context["extra_booking_wait"] = spell_minutes(settings.extra_booking_minutes)

        # Everything each card needs to draw its own booking button, worked out
        # here in a handful of queries. Doing it in the template instead would
        # cost several queries per card.
        booked_ids = set()
        waitlisted_ids = set()
        waitlist_positions = {}
        held_by_date = defaultdict(list)
        if member and instances:
            dates = {instance.date for instance in instances}
            booked_ids = set(
                member.booked_classes.filter(date__in=dates).values_list(
                    "id", flat=True
                )
            )
            waitlisted_ids = set(
                member.waitlisted_classes.filter(date__in=dates).values_list(
                    "id", flat=True
                )
            )
            waitlist_positions = self._waitlist_positions(member, waitlisted_ids)
            # Counted per date over every class that day, not just the ones still
            # listed here: a class that already started this morning is gone from
            # the list but still uses up the member's quota for today.
            for held in member_classes_on_dates(member, dates):
                held.member_is_waitlisted = held.id in waitlisted_ids
                held_by_date[held.date].append(held)

        date_groups = []
        for instance in instances:
            max_members = instance.class_schedule.class_obj.max_members
            booked_count = getattr(instance, "booked_count", 0)
            instance.slots_left = max(0, max_members - booked_count)
            instance.booked_percent = (
                min(100, round(booked_count * 100 / max_members)) if max_members else 0
            )
            # A few faces so booking feels like joining people, not reserving a
            # slot. By name, so the row is stable between page loads (Member's
            # own ordering is newest first, which would look random here).
            booked_members = sorted(
                instance.booked_members.all(), key=lambda m: m.name.lower()
            )[:5]
            instance.booked_preview = [
                {"initial": m.name[:1].upper(), "first_name": m.name.split()[0]}
                for m in booked_members
                if m.name
            ]
            instance.booked_extra = max(0, booked_count - len(booked_members))
            instance.member_is_booked = instance.id in booked_ids
            instance.member_is_waitlisted = instance.id in waitlisted_ids
            instance.waitlist_place = waitlist_positions.get(instance.id)
            instance.booking_block = None
            if (
                member
                and not instance.member_is_booked
                and not instance.member_is_waitlisted
            ):
                instance.booking_block = booking_block_reason(
                    member,
                    instance,
                    held_that_day=len(held_by_date[instance.date]),
                    now=now,
                    settings=settings,
                )
            _attach_cancel_window(instance, now, settings)

            if not date_groups or date_groups[-1]["date"] != instance.date:
                held = held_by_date[instance.date]
                date_groups.append(
                    {
                        "date": instance.date,
                        "instances": [],
                        "held_classes": held,
                        "day_limit_reached": (
                            len(held) >= settings.advance_classes_per_day
                        ),
                    }
                )
            date_groups[-1]["instances"].append(instance)

        context["date_groups"] = date_groups
        return context

    @staticmethod
    def _waitlist_positions(member, instance_ids):
        """{instance_id: place in the queue} for the member's waitlisted classes.

        One query for every card, instead of ClassInstance.waitlist_position()
        per card. Same FIFO order (through table id).
        """
        if not instance_ids:
            return {}
        through = ClassInstance.waitlisted_members.through
        places = {}
        seen = defaultdict(int)
        for instance_id, member_id in (
            through.objects.filter(classinstance_id__in=instance_ids)
            .order_by("id")
            .values_list("classinstance_id", "member_id")
        ):
            seen[instance_id] += 1
            if member_id == member.id:
                places[instance_id] = seen[instance_id]
        return places


class ClassDetailView(MemberRequiredMixin, DetailView):
    model = ClassInstance
    template_name = "classes/class_detail.html"
    context_object_name = "instance"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_email = self.request.session.get("member_email")
        member = None
        if member_email:
            try:
                member = Member.objects.get(email=member_email)
            except Member.DoesNotExist:
                member = None
        context["member"] = member

        # Tell the member up front why they cannot book, instead of letting them
        # tap Booking and get an error.
        now = timezone.now()
        settings = PenaltySettings.get_solo()
        context["rules"] = settings
        context["advance_classes_per_day"] = settings.advance_classes_per_day
        context["extra_booking_wait"] = spell_minutes(settings.extra_booking_minutes)
        _attach_cancel_window(self.object, now, settings)

        classes_on_date = (
            list(member_classes_on_date(member, self.object.date)) if member else []
        )
        context["member_classes_on_date"] = classes_on_date

        block = None
        if member and member not in list(self.object.booked_members.all()) + list(
            self.object.waitlisted_members.all()
        ):
            block = booking_block_reason(
                member,
                self.object,
                held_that_day=len(classes_on_date),
                now=now,
                settings=settings,
            )
        context["booking_block"] = block
        context["day_limit_reached"] = bool(block) and block["code"] == "DAY_LIMIT"

        context["waitlist_place"] = (
            self.object.waitlist_position(member) if member else None
        )

        # "Ajak temen": prefilled WhatsApp message with a link to this class
        context["whatsapp_share_url"] = whatsapp_invite_url(
            self.object, self.request.build_absolute_uri()
        )
        return context


def class_rules(request):
    """Aturan Kelas: the three rules, in words a member can act on.

    Open to anyone, not gated behind login, because its main job is to be a link
    an admin can paste into a WhatsApp reply and be done. Explaining the rule one
    member at a time is the thing this page exists to stop.

    Everything on it reads the live settings row, so the day an admin changes the
    window in /admin, the page changes with it and nobody is reading last month's
    rules.
    """
    settings = PenaltySettings.get_solo()
    member = None
    email = request.session.get("member_email")
    if email:
        member = Member.objects.filter(email=email).first()

    # A worked example beats a rule. Built from a real evening class so the
    # times look like the ones on their own booking.
    example_start = timezone.localtime(timezone.now()).replace(
        hour=17, minute=15, second=0, microsecond=0
    )
    example_deadline = example_start - timedelta(hours=settings.late_cancel_hours)
    example_opens = example_start - timedelta(minutes=settings.extra_booking_minutes)

    return render(
        request,
        "classes/class_rules.html",
        {
            "rules": settings,
            "member": member,
            "cancel_wait": spell_minutes(settings.late_cancel_hours * 60),
            "extra_booking_wait": spell_minutes(settings.extra_booking_minutes),
            "strikes_before_ban": settings.misses_allowed + 1,
            "example_start": example_start,
            "example_deadline": example_deadline,
            "example_opens": example_opens,
            "example_late": example_start - timedelta(minutes=30),
            "class_penalty": member_state(member) if member else None,
        },
    )


@member_login_required
def class_calendar(request, instance_id):
    """Download this class as an .ics, so it lands in the member's own calendar.

    Only for members who actually hold a spot: the point is remembering a class
    you signed up for, and the calendar app's own alarm is a reminder we do not
    have to send ourselves.
    """
    instance = get_object_or_404(
        ClassInstance.objects.select_related("class_schedule__class_obj"),
        id=instance_id,
    )
    member = get_object_or_404(Member, email=request.session.get("member_email"))

    if (
        member not in instance.booked_members.all()
        and member not in instance.waitlisted_members.all()
    ):
        messages.warning(
            request,
            "Kamu belum terdaftar di kelas ini, jadi belum bisa ditambahkan ke kalender.",
        )
        return redirect("classes:class_detail", pk=instance.id)

    detail_url = request.build_absolute_uri(
        reverse("classes:class_detail", args=[instance.id])
    )
    response = HttpResponse(
        class_instance_to_ics(instance, url=detail_url),
        content_type="text/calendar; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{ics_filename(instance)}"'
    )
    return response


def _redirect_after_action(request, instance):
    """Send the member back where they booked from.

    The class list posts next=list so a one-tap booking returns to the list,
    scrolled to that same card, instead of dropping them on the detail page.
    /akun posts next=akun for the same reason: a member cancelling from their own
    upcoming list should land back on their own upcoming list. Only these fixed
    values are accepted, so it can't be used as an open redirect the way an
    arbitrary next=<url> could.
    """
    target = request.POST.get("next")
    if target == "list":
        return redirect(f"{reverse('classes:class_list')}#kelas-{instance.id}")
    if target == "akun":
        return redirect("member_details")
    return redirect("classes:class_detail", pk=instance.id)


@require_POST
@member_login_required
def book_class(request, instance_id):
    instance = get_object_or_404(ClassInstance, id=instance_id)
    member = get_object_or_404(Member, email=request.session.get("member_email"))

    # Check if already registered
    if (
        member in instance.booked_members.all()
        or member in instance.waitlisted_members.all()
    ):
        messages.warning(request, "Anda sudah terdaftar di kelas ini.")
        return _redirect_after_action(request, instance)

    with transaction.atomic():
        # Lock the member so two fast taps cannot both slip past the daily limit.
        Member.objects.select_for_update().get(pk=member.pk)

        # Membership access and the max classes per day rule, counted fresh inside
        # the lock. Same helper the buttons use, so the two can never disagree.
        block = booking_block_reason(member, instance)
        if block:
            messages.error(request, block["message"])
            return _redirect_after_action(request, instance)

        # Check if there are available slots
        if (
            instance.booked_members.count()
            < instance.class_schedule.class_obj.max_members
        ):
            instance.booked_members.add(member)
            messages.success(
                request,
                f"Berhasil booking kelas {instance.class_schedule.class_obj.name}.",
            )
        else:
            instance.waitlisted_members.add(member)
            messages.info(
                request,
                f"Kelas penuh. Anda dimasukkan ke daftar tunggu untuk kelas {instance.class_schedule.class_obj.name}.",
            )

    instance.update_status()
    return _redirect_after_action(request, instance)


@require_POST
@member_login_required
def cancel_class(request, instance_id):
    instance = get_object_or_404(ClassInstance, id=instance_id)
    member = get_object_or_404(Member, email=request.session.get("member_email"))

    if member in instance.booked_members.all():
        # Decided before the booking is removed, since the rule is about this
        # member holding this seat this close to the class. Waitlist places never
        # come through here: leaving a queue costs nobody a seat.
        settings = PenaltySettings.get_solo()
        miss = record_late_cancel(member, instance, settings=settings)

        instance.booked_members.remove(member)
        instance.move_from_waitlist()

        class_name = instance.class_schedule.class_obj.name
        if miss:
            messages.warning(
                request,
                f"Booking kelas {class_name} sudah dibatalkan. Tapi karena "
                f"kurang dari {spell_minutes(settings.late_cancel_hours * 60)} "
                f"sebelum kelas mulai, ini dihitung 1 kali buang tempat, sama "
                f"kayak nggak dateng. Lain kali batalin lebih awal ya.",
            )
        else:
            messages.success(
                request,
                f"Booking kelas {class_name} sudah dibatalkan. Makasih udah "
                f"batalin dari jauh-jauh hari, tempatnya jadi kepakai member lain.",
            )
    elif member in instance.waitlisted_members.all():
        instance.waitlisted_members.remove(member)
        messages.success(
            request,
            f"Anda telah dihapus dari daftar tunggu untuk kelas {instance.class_schedule.class_obj.name}.",
        )

    instance.update_status()
    return _redirect_after_action(request, instance)
