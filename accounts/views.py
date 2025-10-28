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


def job_openings(request):
    return render(request, "lowongan-kerja.html")


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
