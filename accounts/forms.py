from django import forms
from django.core.exceptions import ValidationError

from .models import Member, Tamu, Masukkan


class MasukkanForm(forms.ModelForm):
    class Meta:
        model = Masukkan
        fields = ["name", "contact", "feedback"]
        widgets = {
            "name": forms.TextInput(),
            "contact": forms.TextInput(),
            "feedback": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Kritik, saran, pertanyaan..."}
            ),
        }
        labels = {
            "name": "Nama",
            "contact": "Kontak (No. WA / Sosial Media, Opsional)",
            "feedback": "Masukkan Anda",
        }


class TamuForm(forms.ModelForm):
    class Meta:
        model = Tamu
        fields = [
            "name",
            "phone_number",
            "has_worked_out_before",
            "social_media_username",
        ]
        widgets = {
            "name": forms.TextInput(),
            "phone_number": forms.TextInput(),
            "has_worked_out_before": forms.TextInput(
                attrs={"placeholder": "misal: belum pernah, 3 bulan, 1 tahun, ..."}
            ),
            "social_media_username": forms.TextInput(),
        }
        labels = {
            "name": "Nama",
            "phone_number": "No. HP",
            "has_worked_out_before": "Udah pernah rutin nge-Gym atau belum?",
            "social_media_username": "Username akun Instagram/TikTok/Facebook (Opsional)",
        }


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
            "address",
            "social_media_username",
            "years_of_working_out",
            "goals",
            "know_mulai_gym_from",
            "why_choose_mulai",
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
            "address",
            "social_media_username",
            "years_of_working_out",
            "goals",
            "know_mulai_gym_from",
            "why_choose_mulai",
        ]
        widgets = {
            "goals": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "misal: supaya lebih sehat, cakep, turunin berat, ototan, ...",
                }
            ),
            "know_mulai_gym_from": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "misal: ngelewat, instagram, tiktok, teman, google maps, ...",
                }
            ),
            "why_choose_mulai": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "misal: nyaman, dekat kantor, murah, ada teman, pelatihnya baik ...",
                }
            ),
            "height": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "tinggi dalam cm"}
            ),
            "weight": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "berat dalam kg"}
            ),
            "address": forms.TextInput(
                attrs={"placeholder": "Sudirman, Kebonjati, Kopo, ..."}
            ),
            "years_of_working_out": forms.TextInput(
                attrs={"placeholder": "belum pernah, 3 bulan, 2 tahun"}
            ),
        }
        labels = {
            "height": "Tinggi (cm)",
            "weight": "Berat (kg)",
            "years_of_working_out": "Sudah pernah nge-Gym berapa lama?",
            "goals": "Tujuan kamu nge-Gym supaya apa?",
            "know_mulai_gym_from": "Kenal Mulai Gym dari mana?",
            "why_choose_mulai": "Kenapa pilih Mulai Gym?",
        }
        help_texts = {
            # Remove help text and use placeholder instead
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

        # Check if phone number contains invalid characters
        if phone_number:
            # First check if the phone number has any disallowed characters
            allowed_chars = set("0123456789- ")
            if not all(char in allowed_chars for char in phone_number):
                raise ValidationError(
                    {"phone_number_display": "Nomor HP hanya boleh berisi angka"}
                )

            # Clean up the phone number by removing spaces and hyphens
            cleaned_phone = "".join(char for char in phone_number if char.isdigit())

            # Validate that there's actual digits after cleanup
            if not cleaned_phone:
                raise ValidationError(
                    {"phone_number_display": "Nomor HP harus berisi angka"}
                )

            # Use the cleaned phone number for further processing
            phone_number = cleaned_phone

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

        # Automatically calculate is_pemula based on years_of_working_out
        years_of_working_out = (
            instance.years_of_working_out.lower()
            if instance.years_of_working_out
            else ""
        )

        if any(
            sub in years_of_working_out
            for sub in ["belum", "belom", "blm", "blum", "belm", "blon", "belon"]
        ):
            instance.is_pemula = True
        elif "tahun" in years_of_working_out:
            instance.is_pemula = False
        else:
            instance.is_pemula = None

        if commit:
            instance.save()
        return instance


class MemberLoginForm(forms.Form):
    email = forms.EmailField(label="Email", required=False)
    country_code = forms.CharField(
        max_length=5,
        initial="+62",
        label="Country Code",
        required=False,
        widget=forms.TextInput(attrs={"style": "width: 80px; display: inline-block;"}),
    )
    phone_number_display = forms.CharField(
        max_length=15,
        label="Phone Number",
        required=False,
        widget=forms.TextInput(
            attrs={
                "style": "width: calc(100% - 95px); display: inline-block; margin-left: 5px;"
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        country_code = cleaned_data.get("country_code", "").strip()
        phone_number = cleaned_data.get("phone_number_display", "").strip()

        # Check if at least one of email or phone number is provided
        if not email and not phone_number:
            raise ValidationError("Mohon masukkan email atau nomor telepon")

        # If phone number is provided, format it properly
        if phone_number:
            # Check if phone number contains invalid characters
            allowed_chars = set("0123456789- ")
            if not all(char in allowed_chars for char in phone_number):
                raise ValidationError(
                    {
                        "phone_number_display": "Phone number should only contain numbers, spaces, and hyphens"
                    }
                )

            # Clean up the phone number by removing spaces and hyphens
            cleaned_phone = "".join(char for char in phone_number if char.isdigit())

            # Validate that there's actual digits after cleanup
            if not cleaned_phone:
                raise ValidationError(
                    {"phone_number_display": "Phone number must contain digits"}
                )

            # Use the cleaned phone number for further processing
            phone_number = cleaned_phone

            # Validate country code format
            if not country_code:
                country_code = "+62"  # Default
            elif not country_code.startswith("+"):
                country_code = "+" + country_code

            # Remove any '+' sign from the phone number part
            if phone_number.startswith("+"):
                phone_number = phone_number[1:]

            # Remove country code from phone number if it's there
            if country_code.startswith("+") and phone_number.startswith(
                country_code[1:]
            ):
                phone_number = phone_number[len(country_code) - 1 :]

            # Remove leading zeros if any
            phone_number = phone_number.lstrip("0")

            # Create the standardized phone number, removing the '+' from country code
            final_phone = country_code.replace("+", "") + phone_number
            cleaned_data["formatted_phone"] = final_phone

        return cleaned_data


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
            "address",
            "years_of_working_out",
            "goals",
            "why_choose_mulai",
        ]
        widgets = {
            "goals": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "misal: supaya lebih sehat, cakep, turunin berat, ototan, ...",
                }
            ),
            "height": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "tinggi dalam cm"}
            ),
            "weight": forms.NumberInput(
                attrs={"step": "0.1", "placeholder": "berat dalam kg"}
            ),
            "address": forms.TextInput(
                attrs={"placeholder": "Sudirman, Kebonjati, Kopo, ..."}
            ),
            "years_of_working_out": forms.TextInput(
                attrs={"placeholder": "belum pernah, 3 bulan, 2 tahun"}
            ),
            "why_choose_mulai": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "misal: nyaman, dekat kantor, murah, ada teman, pelatihnya baik ...",
                }
            ),
        }
        labels = {
            "height": "Tinggi (cm)",
            "weight": "Berat (kg)",
            "years_of_working_out": "Sudah pernah nge-Gym berapa lama?",
            "goals": "Tujuan kamu nge-Gym supaya apa?",
            "why_choose_mulai": "Kenapa pilih Mulai Gym?",
        }
        help_texts = {
            # Remove help text and use placeholder instead
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

        # Check if phone number contains invalid characters
        if phone_number:
            # First check if the phone number has any disallowed characters
            allowed_chars = set("0123456789- ")
            if not all(char in allowed_chars for char in phone_number):
                raise ValidationError(
                    {
                        "phone_number_display": "Phone number should only contain numbers, spaces, and hyphens"
                    }
                )

            # Clean up the phone number by removing spaces and hyphens
            cleaned_phone = "".join(char for char in phone_number if char.isdigit())

            # Validate that there's actual digits after cleanup
            if not cleaned_phone:
                raise ValidationError(
                    {"phone_number_display": "Phone number must contain digits"}
                )

            # Use the cleaned phone number for further processing
            phone_number = cleaned_phone

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
