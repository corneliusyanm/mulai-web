from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic import DetailView, TemplateView
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

# How many rows each history section shows on /akun/ before the member has to
# open /akun/riwayat/ for the full list.
RECENT_VISITS_LIMIT = 5
RECENT_PAYMENTS_LIMIT = 5
PAST_CLASSES_LIMIT = 10

HISTORY_TABS = [
    {"key": "kunjungan", "label": "Kunjungan", "icon": "fas fa-calendar-check"},
    {"key": "pembayaran", "label": "Pembayaran", "icon": "fas fa-credit-card"},
    {"key": "kelas", "label": "Kelas", "icon": "fas fa-dumbbell"},
]

MONTHS_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


def _duration_label(check_in, check_out):
    """Human duration of a visit, e.g. "1j 18m". Empty when still checked in."""
    if not check_in or not check_out:
        return ""
    minutes = int((check_out - check_in).total_seconds() // 60)
    if minutes < 1:
        return "< 1m"
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}j {minutes}m"
    if hours:
        return f"{hours}j"
    return f"{minutes}m"


def _group_by_month(rows, get_date):
    """Bucket rows (already sorted newest first) into month groups for display."""
    groups = []
    for row in rows:
        row_date = get_date(row)
        key = (row_date.year, row_date.month)
        if not groups or groups[-1]["key"] != key:
            groups.append(
                {
                    "key": key,
                    "label": f"{MONTHS_ID[row_date.month]} {row_date.year}",
                    "rows": [],
                }
            )
        groups[-1]["rows"].append(row)
    return groups


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

        past_booked = member.booked_classes.filter(date__lt=today)
        past_waitlisted = member.waitlisted_classes.filter(date__lt=today)

        # Filter booked classes for upcoming and past
        context["upcoming_booked_classes"] = member.booked_classes.filter(
            date__gte=today
        ).order_by("date", "start_time")
        context["past_booked_classes"] = past_booked.order_by("-date", "-start_time")[
            :PAST_CLASSES_LIMIT
        ]

        # Filter waitlisted classes for upcoming and past
        context["upcoming_waitlisted_classes"] = member.waitlisted_classes.filter(
            date__gte=today
        ).order_by("date", "start_time")
        context["past_waitlisted_classes"] = past_waitlisted.order_by(
            "-date", "-start_time"
        )[:PAST_CLASSES_LIMIT]

        context["recent_visits"] = Visit.objects.filter(member=member).order_by(
            "-check_in_time"
        )[:RECENT_VISITS_LIMIT]
        context["recent_payments"] = Payment.objects.filter(member=member).order_by(
            "-payment_date"
        )[:RECENT_PAYMENTS_LIMIT]

        # Totals drive the "Lihat Semua Riwayat" buttons, which only make sense
        # when there is more history than the trimmed lists above show.
        total_visits = Visit.objects.filter(member=member).count()
        total_payments = Payment.objects.filter(member=member).count()
        past_booked_count = past_booked.count()
        past_waitlisted_count = past_waitlisted.count()

        context["total_visits"] = total_visits
        context["total_payments"] = total_payments
        context["total_past_classes"] = past_booked_count + past_waitlisted_count
        context["has_more_visits"] = total_visits > RECENT_VISITS_LIMIT
        context["has_more_payments"] = total_payments > RECENT_PAYMENTS_LIMIT
        context["has_more_past_classes"] = (
            past_booked_count > PAST_CLASSES_LIMIT
            or past_waitlisted_count > PAST_CLASSES_LIMIT
        )
        return context


class MemberHistoryView(MemberRequiredMixin, TemplateView):
    """Full history for the logged-in member: every visit, payment and past class.

    Unlike /akun/ (which trims each list), nothing is cut off here. Only the
    active tab's rows are loaded, grouped by month so long lists stay readable.
    """

    template_name = "accounts/member_history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = Member.objects.get(email=self.request.session["member_email"])
        today = timezone.now().date()

        tab = self.request.GET.get("tab", HISTORY_TABS[0]["key"])
        if tab not in [t["key"] for t in HISTORY_TABS]:
            tab = HISTORY_TABS[0]["key"]

        visits = Visit.objects.filter(member=member)
        payments = Payment.objects.filter(member=member)
        past_booked = member.booked_classes.filter(date__lt=today)
        past_waitlisted = member.waitlisted_classes.filter(date__lt=today)

        counts = {
            "kunjungan": visits.count(),
            "pembayaran": payments.count(),
            "kelas": past_booked.count() + past_waitlisted.count(),
        }

        groups = []
        stats = []

        if tab == "kunjungan":
            rows = list(visits.order_by("-check_in_time"))
            for visit in rows:
                visit.duration_label = _duration_label(
                    visit.check_in_time, visit.check_out_time
                )
            groups = _group_by_month(rows, lambda v: localtime(v.check_in_time).date())
            this_month = sum(
                1
                for v in rows
                if localtime(v.check_in_time).date().replace(day=1)
                == today.replace(day=1)
            )
            stats = [
                {
                    "label": "Total Kunjungan",
                    "value": counts["kunjungan"],
                    "icon": "fas fa-calendar-check",
                },
                {
                    "label": "Bulan Ini",
                    "value": this_month,
                    "icon": "fas fa-calendar-day",
                },
                {
                    "label": "Pertama Kali",
                    "value": localtime(rows[-1].check_in_time).strftime("%d %b %Y")
                    if rows
                    else "-",
                    "icon": "fas fa-flag",
                },
            ]
        elif tab == "pembayaran":
            rows = list(payments.select_related("package").order_by("-payment_date"))
            groups = _group_by_month(rows, lambda p: localtime(p.payment_date).date())
            total_paid = sum(p.amount for p in rows)
            stats = [
                {
                    "label": "Total Transaksi",
                    "value": counts["pembayaran"],
                    "icon": "fas fa-receipt",
                },
                {
                    "label": "Total Dibayar",
                    "value": f"Rp {total_paid:,.0f}",
                    "icon": "fas fa-wallet",
                },
                {
                    "label": "Terakhir",
                    "value": localtime(rows[0].payment_date).strftime("%d %b %Y")
                    if rows
                    else "-",
                    "icon": "fas fa-clock-rotate-left",
                },
            ]
        else:
            booked = past_booked.select_related("class_schedule__class_obj")
            waitlisted = past_waitlisted.select_related("class_schedule__class_obj")
            rows = [{"instance": ci, "is_waitlist": False} for ci in booked] + [
                {"instance": ci, "is_waitlist": True} for ci in waitlisted
            ]
            rows.sort(
                key=lambda row: (row["instance"].date, row["instance"].start_time),
                reverse=True,
            )
            groups = _group_by_month(rows, lambda row: row["instance"].date)
            stats = [
                {
                    "label": "Kelas Diikuti",
                    "value": booked.count(),
                    "icon": "fas fa-dumbbell",
                },
                {
                    "label": "Pernah Antri",
                    "value": waitlisted.count(),
                    "icon": "fas fa-hourglass-half",
                },
                {
                    "label": "Terakhir",
                    "value": rows[0]["instance"].date.strftime("%d %b %Y")
                    if rows
                    else "-",
                    "icon": "fas fa-clock-rotate-left",
                },
            ]

        context["member"] = member
        context["active_tab"] = tab
        context["tabs"] = [{**t, "count": counts[t["key"]]} for t in HISTORY_TABS]
        context["stats"] = stats
        context["groups"] = groups
        context["total_rows"] = counts[tab]
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
