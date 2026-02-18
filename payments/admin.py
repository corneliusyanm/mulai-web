from django import forms
from django.contrib.admin import widgets

from .models import Payment


class PaymentAdminForm(forms.ModelForm):
    payment_date = forms.SplitDateTimeField(widget=widgets.AdminSplitDateTime())

    class Meta:
        model = Payment
        fields = (
            "member",
            "package",
            "amount",
            "payment_date",
            "payment_method",
            "apakah_nyicil",
            "skip_membership_update",
            "notes",
        )
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-control"}),
            "apakah_nyicil": forms.RadioSelect(
                choices=[(True, "Ya"), (False, "Tidak")]
            ),
            "skip_membership_update": forms.RadioSelect(
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

        # Configure skip_membership_update field
        if "skip_membership_update" in self.fields:
            self.fields["skip_membership_update"].label = (
                "Skip otomatis update membership?"
            )
            self.fields["skip_membership_update"].help_text = (
                "Jika Ya, admin harus update membership secara manual"
            )
            self.fields["skip_membership_update"].widget.choices = [
                (True, "Ya"),
                (False, "Tidak"),
            ]
            self.fields["skip_membership_update"].initial = False

            # When cicilan: auto Ya, non-editable (admin must manually update membership)
            is_cicilan = False
            if self.instance and self.instance.apakah_nyicil:
                is_cicilan = True
            elif self.is_bound and self.data.get("apakah_nyicil") in (True, "True", "true"):
                is_cicilan = True
            if is_cicilan:
                self.fields["skip_membership_update"].initial = True
                self.fields["skip_membership_update"].disabled = True
                self.fields["skip_membership_update"].help_text = (
                    "Otomatis Ya untuk cicilan — admin wajib update membership manual"
                )

    def clean(self):
        cleaned = super().clean()
        if cleaned is None:
            return cleaned
        # When cicilan, enforce skip_membership_update=True (disabled fields don't submit)
        if cleaned.get("apakah_nyicil"):
            cleaned["skip_membership_update"] = True
        return cleaned
