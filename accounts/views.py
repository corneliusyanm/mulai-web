from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from payments.models import Payment
from visits.models import Visit

from .forms import (
    MemberEditForm,
    MemberLoginForm,
    MemberSignUpForm,
    TamuForm,
    MasukkanForm,
)
from .models import Member, Tamu, Masukkan

# Create your views here.


class MemberSignUpView(CreateView):
    model = Member
    form_class = MemberSignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("signup_success")

    def form_valid(self, form):
        member = form.save()
        # Log the member in after signup by storing their email
        self.request.session["member_email"] = member.email
        return super().form_valid(form)


def signup_success(request):
    return render(request, "accounts/signup_success.html")


def member_login(request):
    if request.method == "POST":
        form = MemberLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            formatted_phone = form.cleaned_data.get("formatted_phone")

            try:
                # First try to find by email if provided
                if email:
                    member = Member.objects.get(email=email)
                # If no email or member not found by email, try by phone
                elif formatted_phone:
                    member = Member.objects.get(phone_number=formatted_phone)
                else:
                    raise Member.DoesNotExist

                # If we get here, we found a member
                request.session["member_email"] = member.email
                return redirect("member_details")

            except Member.DoesNotExist:
                messages.error(
                    request,
                    "Member tidak ditemukan. Silakan periksa kembali email atau nomor telepon Anda.",
                )
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = MemberLoginForm()
    return render(request, "accounts/login.html", {"form": form})


def member_logout(request):
    request.session.pop("member_email", None)
    return redirect("member_login")


class MemberRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        member_email = request.session.get("member_email")
        if not member_email:
            return redirect("member_login")
        return super().dispatch(request, *args, **kwargs)


class MemberDetailView(MemberRequiredMixin, DetailView):
    model = Member
    template_name = "accounts/member_details.html"
    context_object_name = "member"

    def get_object(self):
        return Member.objects.get(email=self.request.session["member_email"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        today = timezone.now().date()

        # Filter booked classes for upcoming and past
        context["upcoming_booked_classes"] = member.booked_classes.filter(
            date__gte=today
        ).order_by("date", "start_time")
        context["past_booked_classes"] = member.booked_classes.filter(
            date__lt=today
        ).order_by("-date", "-start_time")[:10]

        # Filter waitlisted classes for upcoming and past
        context["upcoming_waitlisted_classes"] = member.waitlisted_classes.filter(
            date__gte=today
        ).order_by("date", "start_time")
        context["past_waitlisted_classes"] = member.waitlisted_classes.filter(
            date__lt=today
        ).order_by("-date", "-start_time")[:10]

        context["recent_visits"] = Visit.objects.filter(member=member).order_by(
            "-check_in_time"
        )[:5]
        context["recent_payments"] = Payment.objects.filter(member=member).order_by(
            "-payment_date"
        )[:5]
        return context


class MemberEditView(MemberRequiredMixin, UpdateView):
    model = Member
    form_class = MemberEditForm
    template_name = "accounts/member_edit.html"
    success_url = reverse_lazy("member_details")

    def get_object(self):
        return Member.objects.get(email=self.request.session["member_email"])

    def form_valid(self, form):
        messages.success(self.request, "Informasi Anda telah berhasil diperbarui.")
        return super().form_valid(form)


def home(request):
    return render(request, "home.html")


JOB_LISTINGS = [
    {
        "id": "admin-front-office",
        "title": "Admin & Front Office (Part Time)",
        "is_active": True,
        "apply_url": "https://docs.google.com/forms/d/e/1FAIpQLSeoLI9VxWRcZqHGJAH3zb154kJU1k9jvlieGngY3OPpGiz2qg/viewform",
        "looking_for": {
            "priority": [
                {
                    "label": "Usia 21-30 tahun minimal pendidikan SMA sederajat",
                    "desc": "",
                },
                {
                    "label": "Memiliki kemampuan komunikasi yang baik dan berpenampilan menarik",
                    "desc": "",
                },
                {
                    "label": "Memiliki semangat tinggi untuk belajar hal & ilmu yang baru.",
                    "desc": "",
                },
                {
                    "label": "Menyukai olahraga dan berpengalaman di bidang sales adalah nilai tambah",
                    "desc": "",
                },
                {
                    "label": "Memiliki keterampilan edit konten adalah nilai tambah",
                    "desc": "",
                },
            ],
            "bonus": [],
            "note": "",
        },
        "responsibilities": [
            "Menjaga Gym shift siang (14.00-21.00) & menjaga kebershihan Gym, sekitar 1-2 shift per minggu",
            "Mengelola akun data member pada website mulaigym",
            "Memberi senyum, salam, sapa pada member yang datang & pergi",
        ],
    },
    {
        "id": "fitness-trainer",
        "title": "Fitness Trainer (Full Time)",
        "is_active": False,
        "apply_url": "https://docs.google.com/forms/d/e/1FAIpQLSfMP0gmgjXRLNts9slQObb2nHpSMK-Fyjch44A0PeL46Bj06Q/viewform?usp=header",
        "looking_for": {
            "priority": [
                {
                    "label": "Ramah & sabar",
                    "desc": "(bisa mendengarkan & membimbing para pemula).",
                },
                {
                    "label": "Kemampuan mengajar & komunikasi",
                    "desc": "(jelaskan gerakan dengan tepat namun mudah dimengerti).",
                },
                {
                    "label": "Semangat belajar",
                    "desc": "(terbuka untuk terus upgrade pengetahuan fitness dan kesehatan).",
                },
            ],
            "bonus": [
                "Sertifikasi/lisensi resmi.",
                "Badan berotot/atletis.",
                "Pengalaman mengajar lama.",
            ],
            "note": "✅ Fresh graduate / pengalaman pertama sebagai trainer dipersilahkan!",
        },
        "responsibilities": [
            "Merancang & memandu program latihan Kelas Pemula.",
            "Menjawab pertanyaan & menunjukkan penggunaan alat serta teknik yang tepat kepada para member.",
            "Memantau kemajuan dan memberi motivasi para member.",
            "Menjaga keamanan, kebersihan, serta suasana nyaman di dalam Gym.",
        ],
    },
    {
        "id": "admin-front-office",
        "title": "Admin & Front Office (Full Time)",
        "is_active": False,
        "apply_url": "https://docs.google.com/forms/d/e/1FAIpQLSfMP0gmgjXRLNts9slQObb2nHpSMK-Fyjch44A0PeL46Bj06Q/viewform?usp=header",
        "looking_for": {
            "priority": [
                {
                    "label": "Wanita usia 21-30 tahun minimal pendidikan SMA sederajat",
                    "desc": "",
                },
                {
                    "label": "Memiliki kemampuan komunikasi yang baik dan berpenampilan menarik",
                    "desc": "",
                },
                {
                    "label": "Memiliki semangat tinggi untuk belajar hal & ilmu yang baru.",
                    "desc": "",
                },
                {
                    "label": "Menyukai olahraga dan berpengalaman di bidang sales adalah nilai tambah",
                    "desc": "",
                },
                {
                    "label": "Memiliki keterampilan edit konten adalah nilai tambah",
                    "desc": "",
                },
            ],
            "bonus": [],
            "note": "",
        },
        "responsibilities": [
            "Menjaga Gym shift siang (14.00-21.00) & menjaga kebershihan Gym",
            "Mengelola akun data member pada website mulaigym",
            "Memberi senyum, salam, sapa pada member yang datang & pergi",
            "Mengelola member & mengembangkan strategi penjualan",
            "Mengelola media sosial mulaigym.id",
        ],
    },
]


def job_openings(request):
    active_jobs = [job for job in JOB_LISTINGS if job["is_active"]]
    closed_jobs = [job for job in JOB_LISTINGS if not job["is_active"]]
    return render(
        request,
        "lowongan-kerja.html",
        {"active_jobs": active_jobs, "closed_jobs": closed_jobs},
    )


def tamu_signup_view(request):
    if request.method == "POST":
        form = TamuForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("tamu_signup_success")
    else:
        form = TamuForm()
    return render(request, "accounts/tamu_signup.html", {"form": form})


def tamu_signup_success_view(request):
    return render(request, "accounts/tamu_signup_success.html")


def masukkan_view(request):
    if request.method == "POST":
        form = MasukkanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("masukkan_success")
    else:
        form = MasukkanForm()
    return render(request, "accounts/masukkan.html", {"form": form})


def masukkan_success_view(request):
    return render(request, "accounts/masukkan_success.html")
