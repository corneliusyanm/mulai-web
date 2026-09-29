from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.forms import MemberLoginForm
from accounts.models import Member
from accounts.views import log_member_in
from classes.reviews import FACES as REVIEW_FACES, pending_reviews

from .models import Visit
from .moments import (
    membership_ending,
    membership_lapsed,
    next_class,
    visit_moment,
    workout_length,
)

# How long the check-in and check-out screens stay up before moving on to /akun.
# Long enough to read a line. Both screens are their own URLs, so reloading one
# changes nothing; the move just takes the member on to their own page.
SUCCESS_SECONDS = 8


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
        return render(
            request,
            "visits/check_in_failed.html",
            {
                "member": member,
                "lapsed": membership_lapsed(member, timezone.localdate()),
                "total_visits": Visit.objects.filter(member=member).count(),
            },
        )

    Visit.objects.get_or_create(
        member=member,
        check_out_time__isnull=True,
        defaults={"check_in_time": timezone.now()},
    )
    return redirect("check_in_success")


def check_in_success(request):
    """The screen a member shows at the desk, plus one or two lines worth reading.

    Shows the latest visit, open or not, so reloading it later never bounces
    anyone back into a check-in they did not ask for.
    """
    member = _session_member(request)
    if member is None:
        return redirect("check_in_page")
    visit = Visit.objects.filter(member=member).order_by("-check_in_time").first()
    if visit is None:
        return redirect("check_in_page")

    return render(
        request,
        "visits/quick_check_in.html",
        {
            "member": member,
            "visit": visit,
            "visit_day": timezone.localdate(visit.check_in_time),
            "moment": visit_moment(member, visit),
            "ending": membership_ending(member, timezone.localdate()),
            "success_seconds": SUCCESS_SECONDS,
        },
    )


def check_out_page(request):
    """Check the member out of their open visit.

    A phone that does not know the member gets the login box first, and checks
    out as soon as it matches someone, the same way /check-in does.
    """
    form = MemberLoginForm(request.POST) if request.method == "POST" else None
    if form is not None:
        if not form.is_valid():
            return render(request, "visits/check_out.html", {"form": form})
        log_member_in(request, form.member)

    member = _session_member(request)
    if member is None:
        return render(request, "visits/check_out.html", {"form": MemberLoginForm()})

    now = timezone.now()
    visit = (
        Visit.objects.filter(member=member, check_out_time__isnull=True)
        .order_by("-check_in_time")
        .first()
    )
    if visit is None:
        # Scanned twice on the way out, or never checked in today. The second
        # one matters: with no check-in today, a class booked today counts as
        # missed, so the screen says to tell the admin.
        done_today = (
            Visit.objects.filter(
                member=member,
                check_out_time__isnull=False,
                check_in_time__date=timezone.localdate(now),
            )
            .order_by("-check_out_time")
            .first()
        )
        return render(
            request,
            "visits/check_out_failed.html",
            {"member": member, "done_today": done_today},
        )

    visit.check_out_time = now
    visit.save()
    # Its own URL, like check-in: a tab left on /check-out and reloaded
    # tomorrow, after a fresh check-in, would otherwise check out again.
    return redirect("check_out_success")


def check_out_success(request):
    """The check-out screen for the latest finished visit.

    No Django message on the way out: this screen already says it worked, and
    a queued message waits for the next page that renders messages, which on a
    shared phone can be the login box in front of somebody else.
    """
    member = _session_member(request)
    if member is None:
        return redirect("check_out_page")
    visit = (
        Visit.objects.filter(member=member, check_out_time__isnull=False)
        .order_by("-check_out_time")
        .first()
    )
    if visit is None:
        return redirect("check_out_page")

    # The best moment to ask how the class was is the one where they are
    # still standing in the room it happened in. Only the newest class
    # here, though: this screen is somebody on their way out of the door,
    # and the account page picks up whatever they leave behind.
    return render(
        request,
        "visits/quick_check_out.html",
        {
            "member": member,
            "visit": visit,
            "visit_day": timezone.localdate(visit.check_out_time),
            "workout": workout_length(visit),
            "next_class": next_class(member, timezone.now()),
            "pending_reviews": pending_reviews(member)[:1],
            "review_faces": REVIEW_FACES,
            "review_next": "akun",
            "success_seconds": SUCCESS_SECONDS,
        },
    )


# Where "Ganti akun" goes afterwards. Only these, never a URL from the request.
# From the check-out screens it has to be check-out: logging in on /check-in
# would check the other account in on its way out of the door.
FORGET_NEXT = {"check_out": "check_out_page"}


def forget_member(request):
    request.session.pop("member_email", None)
    # Anything still queued was for the member who just left this phone.
    for _ in messages.get_messages(request):
        pass
    return redirect(FORGET_NEXT.get(request.GET.get("next"), "check_in_page"))
