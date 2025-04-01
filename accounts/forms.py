from django import forms
from django.core.exceptions import ValidationError

from .models import Member


class MemberSignUpForm(forms.ModelForm):
    country_code = forms.CharField(
        max_length=5,
        initial="+62",
        label="Country Code",
        widget=forms.TextInput(attrs={"style": "width: 80px; display: inline-block;"}),
    )
    phone_number_display = forms.CharField(
        max_length=15,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "style": "width: calc(100% - 95px); display: inline-block; margin-left: 5px;"
            }
        ),
    )

    class Meta:
        model = Member
        fields = [
            "name",
            "email",
            # Phone number fields are handled separately
            "gender",
            "age",
            "height",
            "weight",
            "years_of_working_out",
            "goals",
            "know_mulai_gym_from",
        ]
        # Define the field order for rendering in the template
        field_order = [
            "name",
            "email",
            "country_code",  # These won't actually be used by the model directly
            "phone_number_display",  # but are included for proper ordering
            "gender",
            "age",
            "height",
            "weight",
            "years_of_working_out",
            "goals",
            "know_mulai_gym_from",
        ]
        widgets = {
            "goals": forms.Textarea(attrs={"rows": 2}),
            "know_mulai_gym_from": forms.Textarea(attrs={"rows": 2}),
            "height": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "Height in cm"}
            ),
            "weight": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "Weight in kg"}
            ),
        }
        labels = {
            "height": "Height (cm)",
            "weight": "Weight (kg)",
            "years_of_working_out": "Years of Working Out",
            "goals": "Goals of Working Out",
            "know_mulai_gym_from": "How did you hear about Mulai Gym?",
        }
        help_texts = {
            "know_mulai_gym_from": "billboard, friends, instagram, google, etc.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If instance exists and has phone_number, pre-fill the fields
        if self.instance and self.instance.phone_number:
            phone = self.instance.phone_number
            # Try to split based on common prefixes, defaults to +62
            if phone.startswith("+"):
                # Handle formats like +628123456789
                prefix = phone[:3]  # e.g., +62
                number = phone[3:]  # e.g., 8123456789
                self.initial["country_code"] = prefix
                self.initial["phone_number_display"] = number
            elif phone.startswith("0"):
                # Handle formats like 08123456789 (Indonesian format)
                self.initial["country_code"] = "+62"
                self.initial["phone_number_display"] = phone[1:]  # Remove leading 0
            else:
                # If format is unknown, just use as-is
                self.initial["country_code"] = "+62"
                self.initial["phone_number_display"] = phone

    def clean(self):
        cleaned_data = super().clean()
        country_code = cleaned_data.get("country_code", "").strip()
        phone_number = cleaned_data.get("phone_number_display", "").strip()

        # Validate country code format
        if not country_code:
            raise ValidationError({"country_code": "Country code is required"})
        if not country_code.startswith("+"):
            country_code = "+" + country_code

        # Remove any '+' sign from the phone number part
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]

        # Remove country code from phone number if it's there
        if country_code.startswith("+") and phone_number.startswith(country_code[1:]):
            phone_number = phone_number[len(country_code) - 1 :]

        # Remove leading zeros if any
        phone_number = phone_number.lstrip("0")

        # Create the standardized phone number, removing the '+' from country code
        final_phone = country_code.replace("+", "") + phone_number

        # Check if this phone number is already in use
        if (
            Member.objects.filter(phone_number=final_phone)
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .exists()
        ):
            raise ValidationError(
                {"phone_number_display": "This phone number is already registered"}
            )

        # Set the cleaned phone_number field
        cleaned_data["phone_number"] = final_phone

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set the phone_number from our cleaned data
        if "phone_number" in self.cleaned_data:
            instance.phone_number = self.cleaned_data["phone_number"]
        if commit:
            instance.save()
        return instance


class MemberLoginForm(forms.Form):
    email = forms.EmailField(label="Email")


class MemberEditForm(forms.ModelForm):
    country_code = forms.CharField(
        max_length=5,
        initial="+62",
        label="Country Code",
        widget=forms.TextInput(attrs={"style": "width: 80px; display: inline-block;"}),
    )
    phone_number_display = forms.CharField(
        max_length=15,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "style": "width: calc(100% - 95px); display: inline-block; margin-left: 5px;"
            }
        ),
    )

    class Meta:
        model = Member
        fields = [
            "name",
            "gender",
            "age",
            "height",
            "weight",
            "years_of_working_out",
            "goals",
        ]
        widgets = {
            "goals": forms.Textarea(attrs={"rows": 2}),
            "height": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "Height in cm"}
            ),
            "weight": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "Weight in kg"}
            ),
        }
        labels = {
            "height": "Height (cm)",
            "weight": "Weight (kg)",
            "years_of_working_out": "Years of Working Out",
            "goals": "Goals of Working Out",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If instance exists and has phone_number, pre-fill the fields
        if self.instance and self.instance.phone_number:
            phone = self.instance.phone_number
            # Try to split based on common prefixes, defaults to +62
            if phone.startswith("+"):
                # Handle formats like +628123456789
                prefix = phone[:3]  # e.g., +62
                number = phone[3:]  # e.g., 8123456789
                self.initial["country_code"] = prefix
                self.initial["phone_number_display"] = number
            elif phone.startswith("0"):
                # Handle formats like 08123456789 (Indonesian format)
                self.initial["country_code"] = "+62"
                self.initial["phone_number_display"] = phone[1:]  # Remove leading 0
            else:
                # If format is unknown, just use as-is with default +62
                if len(phone) > 2 and phone[:2].isdigit():
                    # Assume the first 2 digits are the country code (e.g., 62)
                    self.initial["country_code"] = "+" + phone[:2]
                    self.initial["phone_number_display"] = phone[2:]
                else:
                    self.initial["country_code"] = "+62"
                    self.initial["phone_number_display"] = phone

    def clean(self):
        cleaned_data = super().clean()
        country_code = cleaned_data.get("country_code", "").strip()
        phone_number = cleaned_data.get("phone_number_display", "").strip()

        # Validate country code format
        if not country_code:
            raise ValidationError({"country_code": "Country code is required"})
        if not country_code.startswith("+"):
            country_code = "+" + country_code

        # Remove any '+' sign from the phone number part
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]

        # Remove country code from phone number if it's there
        if country_code.startswith("+") and phone_number.startswith(country_code[1:]):
            phone_number = phone_number[len(country_code) - 1 :]

        # Remove leading zeros if any
        phone_number = phone_number.lstrip("0")

        # Create the standardized phone number, removing the '+' from country code
        final_phone = country_code.replace("+", "") + phone_number

        # Check if this phone number is already in use by another member
        if (
            Member.objects.filter(phone_number=final_phone)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError(
                {"phone_number_display": "This phone number is already registered"}
            )

        # Set the cleaned phone_number field
        cleaned_data["phone_number"] = final_phone

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set the phone_number from our cleaned data
        if "phone_number" in self.cleaned_data:
            instance.phone_number = self.cleaned_data["phone_number"]
        if commit:
            instance.save()
        return instance
