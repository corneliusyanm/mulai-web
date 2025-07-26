from django import forms
from django.contrib.admin import widgets

from .models import Payment


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = (
            "member",
            "package",
            "amount",
            "duration_choice",
            "duration_days",
            "payment_date",
            "payment_method",
            "apakah_nyicil",
            "notes",
        )
        widgets = {
            "payment_date": widgets.AdminSplitDateTime(),
            "duration_choice": forms.RadioSelect(),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
            "apakah_nyicil": forms.RadioSelect(
                choices=[(True, "Ya"), (False, "Tidak")]
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the display of packages in the dropdown to only show the code
        if "package" in self.fields:
            self.fields["package"].label_from_instance = lambda obj: obj.code

        # Configure apakah_nyicil field
        if "apakah_nyicil" in self.fields:
            self.fields["apakah_nyicil"].label = "Apakah bagian dari cicilan?"
            self.fields["apakah_nyicil"].widget.choices = [
                (True, "Ya"),
                (False, "Tidak"),
            ]
            self.fields["apakah_nyicil"].initial = False

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
