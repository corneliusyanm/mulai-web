from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from payments.models import Payment
from visits.models import Visit

from .forms import MemberEditForm, MemberLoginForm, MemberSignUpForm
from .models import Member

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
                    "Member not found. Please check your email or phone number.",
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
        messages.success(
            self.request, "Your information has been updated successfully."
        )
        return super().form_valid(form)


def home(request):
    return render(request, "home.html")
