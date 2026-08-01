from collections import defaultdict
from urllib.parse import quote

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
from .templatetags.class_extras import indonesian_day
from .models import (
    MAX_CLASSES_PER_DAY,
    ClassInstance,
    Member,
    booking_block_reason,
    member_classes_on_date,
    member_classes_on_dates,
)


def member_login_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if "member_email" not in request.session:
            return redirect("member_login")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# Create your views here.


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
        context["max_classes_per_day"] = MAX_CLASSES_PER_DAY

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
                    member, instance, held_that_day=len(held_by_date[instance.date])
                )

            if not date_groups or date_groups[-1]["date"] != instance.date:
                held = held_by_date[instance.date]
                date_groups.append(
                    {
                        "date": instance.date,
                        "instances": [],
                        "held_classes": held,
                        "day_limit_reached": len(held) >= MAX_CLASSES_PER_DAY,
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
        context["max_classes_per_day"] = MAX_CLASSES_PER_DAY
        classes_on_date = (
            list(member_classes_on_date(member, self.object.date)) if member else []
        )
        context["member_classes_on_date"] = classes_on_date

        block = None
        if member and member not in list(self.object.booked_members.all()) + list(
            self.object.waitlisted_members.all()
        ):
            block = booking_block_reason(
                member, self.object, held_that_day=len(classes_on_date)
            )
        context["booking_block"] = block
        context["day_limit_reached"] = bool(block) and block["code"] == "DAY_LIMIT"

        context["waitlist_place"] = (
            self.object.waitlist_position(member) if member else None
        )

        # "Ajak temen": prefilled WhatsApp message with a link to this class
        class_name = self.object.class_schedule.class_obj.name
        share_text = (
            f"Yuk ikut kelas {class_name} di Mulai Gym, "
            f"{indonesian_day(self.object.date)} jam "
            f"{self.object.start_time.strftime('%H:%M')}. "
            f"Detailnya di sini: {self.request.build_absolute_uri()}"
        )
        context["whatsapp_share_url"] = f"https://wa.me/?text={quote(share_text)}"
        return context


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
    Only this one fixed value is accepted, so it can't be used as an open
    redirect the way an arbitrary next=<url> could.
    """
    if request.POST.get("next") == "list":
        return redirect(f"{reverse('classes:class_list')}#kelas-{instance.id}")
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
        instance.booked_members.remove(member)
        instance.move_from_waitlist()
        messages.success(
            request,
            f"Booking Anda untuk kelas {instance.class_schedule.class_obj.name} telah dibatalkan.",
        )
    elif member in instance.waitlisted_members.all():
        instance.waitlisted_members.remove(member)
        messages.success(
            request,
            f"Anda telah dihapus dari daftar tunggu untuk kelas {instance.class_schedule.class_obj.name}.",
        )

    instance.update_status()
    return _redirect_after_action(request, instance)
