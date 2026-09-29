from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.forms import MemberLoginForm
from accounts.models import Member
from accounts.views import log_member_in
from classes.reviews import FACES as REVIEW_FACES, pending_reviews

from .models import Visit


def _session_member(request):
    """The member this phone is logged in as, or None.

    A session naming a member who no longer exists is cleared, so the next
    page shows the login box instead of failing the same way again.
    """
    email = request.session.get("member_email")
    if not email:
        return None
    member = Member.objects.filter(email=email).first()
    if member is None:
        request.session.pop("member_email", None)
    return member


def check_in_page(request):
    """Check in straight away when this phone knows the member.

    Otherwise show the login box, and check in as soon as it matches someone.
    Checking in twice is harmless: an open visit is reused, not duplicated.
    """
    form = MemberLoginForm(request.POST) if request.method == "POST" else None
    if form is not None:
        if not form.is_valid():
            return render(request, "visits/check_in.html", {"form": form})
        log_member_in(request, form.member)

    member = _session_member(request)
    if member is None:
        return render(request, "visits/check_in.html", {"form": MemberLoginForm()})

    if not member.is_active_member:
        return render(request, "visits/check_in_failed.html", {"member": member})

    Visit.objects.get_or_create(
        member=member,
        check_out_time__isnull=True,
        defaults={"check_in_time": timezone.now()},
    )
    return redirect("check_in_success")


def check_in_success(request):
    member_email = request.session.get("member_email")
    if not member_email:
        return redirect("check_in_page")

    try:
        member = Member.objects.get(email=member_email)
        # Show the most recent visit, active or not.
        visit = Visit.objects.filter(member=member).latest("check_in_time")
        # The success page is shown, but its state depends on the visit.
        return render(
            request,
            "visits/quick_check_in.html",
            {"member": member, "visit": visit, "success": True},
        )
    except (Member.DoesNotExist, Visit.DoesNotExist):
        # Only redirect if member has no session or has never visited.
        return redirect("check_in_page")


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

            messages.success(
                request, f"Selamat tinggal, {member.name}! Check-out berhasil."
            )
            # The best moment to ask how the class was is the one where they are
            # still standing in the room it happened in. Only the newest class
            # here, though: this screen is somebody on their way out of the door,
            # and the account page picks up whatever they leave behind.
            return render(
                request,
                "visits/quick_check_out.html",
                {
                    "member": member,
                    "success": True,
                    "visit": visit,
                    "pending_reviews": pending_reviews(member)[:1],
                    "review_faces": REVIEW_FACES,
                    "review_next": "akun",
                },
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
