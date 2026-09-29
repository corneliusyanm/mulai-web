from django import forms
from django.core.exceptions import ValidationError

from .models import Member, Tamu, Masukkan

# Constants for is_pemula calculation
BELUM_VARIATIONS = ["belum", "belom", "blm", "blum", "belm", "blon", "belon"]
TAHUN_VARIATIONS = ["tahun", "thn", "year"]

# Shortest Indonesian mobile number with its 62 prefix. Anything shorter is a
# typo, and matching it could only find the wrong person.
MIN_PHONE_DIGITS = 9

EMAIL_TAKEN = "Email ini udah terdaftar. Coba masuk aja, atau tanya admin."
PHONE_TAKEN = "Nomor ini udah terdaftar. Coba masuk aja, atau tanya admin."


class MasukkanForm(forms.ModelForm):
    class Meta:
        model = Masukkan
        fields = ["topic", "name", "contact", "feedback"]
        widgets = {
            "topic": forms.RadioSelect(),
            "name": forms.TextInput(),
            "contact": forms.TextInput(),
            "feedback": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Kritik, saran, pertanyaan..."}
            ),
        }
        labels = {
            "topic": "Soal apa?",
            "name": "Nama (boleh dikosongin)",
            "contact": "No. WA atau sosmed (boleh dikosongin)",
            "feedback": "Masukanmu",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A RadioSelect on a blank=True field offers an empty "---------" choice;
        # not choosing a chip already means that.
        self.fields["topic"].choices = Masukkan.TOPIC_CHOICES
        self.fields["topic"].required = False


def member_style_phone(raw):
    """Any way an Indonesian number gets typed, as digits starting 62.

    That is how member numbers are stored, so a guest can be matched to the
    membership they buy later. "0812", "812", "+62 812", "+62 0812" (country code
    plus the trunk zero) and "0062 812" all come out as "62812...".
    """
    digits = "".join(ch for ch in raw or "" if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("620"):
        digits = "62" + digits[3:]
    elif digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return digits


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
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone_number": forms.TextInput(
                attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "0812..."}
            ),
            "has_worked_out_before": forms.TextInput(
                attrs={"placeholder": "misal: belum pernah, 3 bulan, 1 tahun, ..."}
            ),
            "social_media_username": forms.TextInput(attrs={"placeholder": "@username"}),
        }
        labels = {
            "name": "Nama",
            "phone_number": "No. HP (WhatsApp)",
            "has_worked_out_before": "Sudah pernah rutin nge-Gym? Kalau sudah, berapa lama?",
            "social_media_username": "Username akun Instagram/TikTok/Facebook (Opsional)",
        }

    def clean_phone_number(self):
        """Saved the way member numbers are (digits, starting 62), not as typed.

        Guests used to be saved as typed, mostly "0812...", while members are
        "62812...", so a guest who later joined could not be matched to their
        membership without rewriting both sides first.
        """
        digits = member_style_phone(self.cleaned_data.get("phone_number", ""))
        if len(digits) < MIN_PHONE_DIGITS:
            raise forms.ValidationError("Nomornya kayaknya kurang, coba cek lagi ya.")
        return digits

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Automatically calculate is_pemula based on has_worked_out_before
        has_worked_out_before = (
            instance.has_worked_out_before.lower()
            if instance.has_worked_out_before
            else ""
        )

        if any(sub in has_worked_out_before for sub in BELUM_VARIATIONS):
            instance.is_pemula = True
        elif any(sub in has_worked_out_before for sub in TAHUN_VARIATIONS):
            instance.is_pemula = False
        else:
            instance.is_pemula = None

        if commit:
            instance.save()
        return instance


# Django's defaults, in the words a member reads on /daftar.
SIGNUP_ERRORS = {
    "required": "Yang ini wajib diisi ya.",
    "invalid_choice": "Pilih salah satu ya.",
    "max_digits": "Angkanya kayaknya kebanyakan, coba cek lagi.",
    "max_whole_digits": "Angkanya kayaknya kebanyakan, coba cek lagi.",
    "max_decimal_places": "Angkanya kayaknya kebanyakan, coba cek lagi.",
    "max_length": "Kepanjangan, coba disingkat ya.",
}


class MemberSignUpForm(forms.ModelForm):
    country_code = forms.CharField(max_length=5, initial="+62", label="Kode negara")
    phone_number_display = forms.CharField(max_length=15, label="Nomor HP (WhatsApp)")

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
            "name": "Nama",
            "email": "Email",
            "gender": "Jenis kelamin",
            "age": "Usia",
            "height": "Tinggi (cm)",
            "weight": "Berat (kg)",
            "address": "Tinggal di daerah mana?",
            "social_media_username": "Instagram / TikTok",
            "years_of_working_out": "Udah pernah rutin nge-gym? Kalau udah, berapa lama?",
            "goals": "Tujuan kamu nge-gym supaya apa?",
            "know_mulai_gym_from": "Kenal Mulai Gym dari mana?",
            "why_choose_mulai": "Kenapa pilih Mulai Gym?",
        }
        error_messages = {"email": {"unique": EMAIL_TAKEN}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Chips, not a dropdown that opens on "---------".
        self.fields["gender"].widget = forms.RadioSelect()
        self.fields["gender"].choices = Member.GENDER_CHOICES
        self.fields["name"].widget.attrs.update({"autocomplete": "name"})
        self.fields["email"].widget.attrs.update(
            {"autocomplete": "email", "autocapitalize": "none", "spellcheck": "false"}
        )
        self.fields["country_code"].widget.attrs.update(
            {"inputmode": "tel", "autocomplete": "tel-country-code"}
        )
        self.fields["phone_number_display"].widget.attrs.update(
            # the +62 is in the box next to it, so no leading 0 here
            {"inputmode": "tel", "autocomplete": "tel-national", "placeholder": "8123..."}
        )
        self.fields["age"].widget.attrs.update({"inputmode": "numeric"})
        # Three boxes share one row on a phone; the unit is in the label, and
        # "tinggi dalam cm" was cut to "tingg".
        for name in ("height", "weight"):
            self.fields[name].widget.attrs.pop("placeholder", None)
            self.fields[name].widget.attrs["inputmode"] = "decimal"
        self.fields["social_media_username"].widget.attrs.update({"placeholder": "@username"})
        # Django's own messages are English; a member signing up reads these.
        for field in self.fields.values():
            field.error_messages.update(SIGNUP_ERRORS)
        self.fields["email"].error_messages["invalid"] = "Email-nya kayaknya belum bener, coba cek lagi."
        for name in ("age", "height", "weight"):
            self.fields[name].error_messages["invalid"] = "Isi pakai angka aja ya."

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

    def clean_email(self):
        # The model's unique check is case-sensitive; the login box is not.
        email = self.cleaned_data["email"]
        if email_taken(email, self.instance):
            raise ValidationError(EMAIL_TAKEN)
        return email

    def clean(self):
        cleaned_data = super().clean()
        country_code = cleaned_data.get("country_code", "").strip()
        phone_number = cleaned_data.get("phone_number_display", "").strip()

        # Validate country code format
        if not country_code:
            raise ValidationError({"country_code": "Kode negaranya diisi ya, misal +62."})
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

        # Taken in any stored format, the same matching the login box uses
        if (
            Member.objects.filter(phone_number__in=phone_candidates(final_phone))
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .exists()
        ):
            raise ValidationError({"phone_number_display": PHONE_TAKEN})

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

        if any(sub in years_of_working_out for sub in BELUM_VARIATIONS):
            instance.is_pemula = True
        elif any(sub in years_of_working_out for sub in TAHUN_VARIATIONS):
            instance.is_pemula = False
        else:
            instance.is_pemula = None

        if commit:
            instance.save()
        return instance


def find_member(identifier):
    """The member an email or a phone number belongs to, or None.

    One box on /masuk, /check-in and /check-out takes either, since members
    remember one or the other. Emails match regardless of case (24 members
    signed up with capitals), and a number matches however it was typed and
    however it was stored: most are "62812...", but a few older rows are
    "0812..." or "ID812...", and those members could never log in by phone.
    """
    raw = (identifier or "").strip()
    if not raw:
        return None

    if "@" in raw:
        exact = Member.objects.filter(email=raw).first()
        if exact:
            return exact
        # Two rows can differ only in case; guessing between them would log
        # somebody into a stranger's account, so that case finds nobody.
        matches = list(Member.objects.filter(email__iexact=raw)[:2])
        return matches[0] if len(matches) == 1 else None

    if len(member_style_phone(raw)) < MIN_PHONE_DIGITS:
        return None
    # Same rule as the email case: one number stored two ways is two people
    # as far as this box can tell, so it finds nobody rather than pick one.
    matches = list(Member.objects.filter(phone_number__in=phone_candidates(raw))[:2])
    return matches[0] if len(matches) == 1 else None


def phone_candidates(raw):
    """Every way the number in `raw` may already be stored, as a list.

    The login box and the "udah terdaftar" checks on /daftar and /akun/ubah
    all use this, so a number cannot be free to register while it already
    logs somebody else in.
    """
    digits = member_style_phone(raw)
    if not digits:
        return []
    local = digits[2:] if digits.startswith("62") else digits
    return list(dict.fromkeys([digits, "0" + local, "ID" + local, local]))


def email_taken(email, instance=None):
    """True when another member already has this email, whatever its case."""
    others = Member.objects.filter(email__iexact=email)
    if instance is not None and instance.pk:
        others = others.exclude(pk=instance.pk)
    return others.exists()




class MemberLoginForm(forms.Form):
    """Email or phone number in one box. The matched member is `self.member`."""

    identifier = forms.CharField(
        label="Email atau nomor HP",
        max_length=254,
        error_messages={"required": "Isi email atau nomor HP kamu dulu ya."},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "placeholder": "0812... atau nama@email.com",
            }
        ),
    )

    def clean_identifier(self):
        identifier = self.cleaned_data["identifier"].strip()
        self.member = find_member(identifier)
        if self.member is None:
            raise ValidationError(
                "Belum ketemu. Coba cek lagi email atau nomor HP-nya, atau tanya admin ya."
            )
        return identifier


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
            raise ValidationError({"country_code": "Kode negaranya diisi ya, misal +62."})
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

        # Taken in any stored format, the same matching the login box uses
        if (
            Member.objects.filter(phone_number__in=phone_candidates(final_phone))
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .exists()
        ):
            raise ValidationError({"phone_number_display": PHONE_TAKEN})

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
