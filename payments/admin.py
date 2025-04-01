from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.utils import timezone

from .models import Payment


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = (
            "member",
            "amount",
            "duration_choice",
            "duration_days",
            "payment_date",
            "payment_method",
            "notes",
        )
        widgets = {
            "payment_date": widgets.AdminSplitDateTime(),
            "duration_choice": forms.RadioSelect(),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide duration_days field initially (will be shown via JavaScript if
        # Custom is selected)
        if "duration_days" in self.fields:
            self.fields["duration_days"].widget.attrs["style"] = "display: none;"
            self.fields["duration_days"].widget.attrs["class"] = "custom-duration-field"

    def clean(self):
        cleaned_data = super().clean()
        duration_choice = cleaned_data.get("duration_choice")
        duration_days = cleaned_data.get("duration_days")

        # If custom duration is selected, duration_days is required
        if duration_choice == 0 and not duration_days:
            self.add_error("duration_days", "Please enter custom duration days")

        return cleaned_data
