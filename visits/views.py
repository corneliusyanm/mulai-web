from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Member
from classes.reviews import FACES as REVIEW_FACES, pending_reviews

from .models import Visit


def check_in_page(request):
    # Handles both manual login (POST) and auto-check-in (GET for logged-in users).
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        country_code = request.POST.get("country_code", "+62").strip()

        if not email and not phone:
            messages.error(request, "Mohon masukkan email atau nomor telepon")
            return redirect("check_in_page")

        try:
            if email:
                member = Member.objects.get(email=email)
            elif phone:
                if not country_code.startswith("+"):
                    country_code = "+" + country_code
                if phone.startswith("+"):
                    phone = phone[1:]
                phone = phone.lstrip("0")
                formatted_phone = country_code.replace("+", "") + phone
                member = Member.objects.get(phone_number=formatted_phone)
            else:
                raise Member.DoesNotExist

            request.session["member_email"] = member.email
            # Fall through to the GET logic after successful login
        except Member.DoesNotExist:
            messages.error(
                request,
                "Member tidak ditemukan. Silakan periksa kembali email atau nomor telepon Anda.",
            )
            return redirect("check_in_page")

    member_email = request.session.get("member_email")
    if member_email:
        try:
            member = Member.objects.get(email=member_email)
            if not member.is_active_member:
                return render(
                    request, "visits/check_in_failed.html", {"member": member}
                )

            # Idempotently create a visit if one isn't active.
            Visit.objects.get_or_create(
                member=member,
                check_out_time__isnull=True,
                defaults={"check_in_time": timezone.now()},
            )
            return redirect("check_in_success")

        except Member.DoesNotExist:
            request.session.pop("member_email", None)

    return render(request, "visits/check_in.html")


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
