from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q

from accounts.views import MemberRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import ClassInstance, Member


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
        all_instances = ClassInstance.objects.filter(
            status__in=["OPEN", "FULL"]
        ).order_by("date", "start_time")

        upcoming_instances = []
        for instance in all_instances:
            # Combine date and start_time into a timezone-aware datetime
            class_dt = timezone.make_aware(
                datetime.combine(instance.date, instance.start_time)
            )

            if class_dt > now:
                upcoming_instances.append(instance)

        return upcoming_instances


class ClassDetailView(MemberRequiredMixin, DetailView):
    model = ClassInstance
    template_name = "classes/class_detail.html"
    context_object_name = "instance"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_email = self.request.session.get("member_email")
        if member_email:
            try:
                context["member"] = Member.objects.get(email=member_email)
            except Member.DoesNotExist:
                context["member"] = None
        else:
            context["member"] = None
        return context


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
        return redirect("classes:class_detail", pk=instance.id)

    # Check if there are available slots
    if instance.booked_members.count() < instance.class_schedule.class_obj.max_members:
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
    return redirect("classes:class_detail", pk=instance.id)


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
    return redirect("classes:class_detail", pk=instance.id)
