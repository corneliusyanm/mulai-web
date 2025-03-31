from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Member

from .models import Visit


def check_in_page(request):
    # If member email is in session, try to auto check-in
    member_email = request.session.get("member_email")
    if member_email:
        try:
            member = Member.objects.get(email=member_email)
            # Check if member is active
            if not member.is_active_member:
                return render(
                    request, "visits/check_in_failed.html", {"member": member}
                )

            # Check if member already has an active visit
            try:
                active_visit = Visit.objects.filter(
                    member=member, check_out_time__isnull=True
                ).latest("check_in_time")
                return render(
                    request,
                    "visits/check_in_failed.html",
                    {"member": member, "has_active_visit": True},
                )
            except Visit.DoesNotExist:
                # No active visit, proceed with check-in
                visit = Visit.objects.create(
                    member=member, check_in_time=timezone.now()
                )
                messages.success(
                    request, f"Welcome, {member.name}! Check-in successful."
                )
                return render(
                    request,
                    "visits/quick_check_in.html",
                    {"member": member, "success": True},
                )
        except Member.DoesNotExist:
            request.session.pop("member_email", None)

    # If not logged in or auto check-in failed, show normal check-in flow
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            member = Member.objects.get(email=email)

            # Check if member is active
            if not member.is_active_member:
                return render(
                    request, "visits/check_in_failed.html", {"member": member}
                )

            # Check if member already has an active visit
            try:
                active_visit = Visit.objects.filter(
                    member=member, check_out_time__isnull=True
                ).latest("check_in_time")
                return render(
                    request,
                    "visits/check_in_failed.html",
                    {"member": member, "has_active_visit": True},
                )
            except Visit.DoesNotExist:
                # No active visit, proceed with check-in
                visit = Visit.objects.create(
                    member=member, check_in_time=timezone.now()
                )
                messages.success(
                    request, f"Welcome, {member.name}! Check-in successful."
                )

                # Store email in session for future quick check-ins
                request.session["member_email"] = email
                return render(
                    request,
                    "visits/quick_check_in.html",
                    {"member": member, "success": True},
                )
        except Member.DoesNotExist:
            messages.error(request, "Member not found. Please check your email.")
            return redirect("check_in_page")

    return render(request, "visits/check_in.html")


def check_out_page(request):
    # Check if user is logged in first
    member_email = request.session.get("member_email")
    if not member_email:
        return render(request, "visits/check_out_failed.html", {"member": None})

    # Try to auto check-out
    try:
        member = Member.objects.get(email=member_email)
        # Find the latest unchecked-out visit
        try:
            visit = Visit.objects.filter(
                member=member, check_out_time__isnull=True
            ).latest("check_in_time")

            visit.check_out_time = timezone.now()
            visit.save()

            messages.success(request, f"Goodbye, {member.name}! Check-out successful.")
            return render(
                request,
                "visits/quick_check_out.html",
                {"member": member, "success": True},
            )
        except Visit.DoesNotExist:
            return render(request, "visits/check_out_failed.html", {"member": member})
    except Member.DoesNotExist:
        request.session.pop("member_email", None)
        return render(request, "visits/check_out_failed.html", {"member": None})

    return render(request, "visits/check_out.html")


def forget_member(request):
    request.session.pop("member_email", None)
    return redirect("check_in_page")
