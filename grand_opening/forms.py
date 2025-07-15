from django import forms
from .models import GrandOpeningRegistration


class GrandOpeningRegistrationForm(forms.ModelForm):
    class Meta:
        model = GrandOpeningRegistration
        fields = [
            "name",
            "phone_number",
            "age",
            "gym_experience",
            "know_mulai_gym_from",
            "social_media_username",
            "visit_schedule",
        ]
        widgets = {
            "name": forms.TextInput(),
            "phone_number": forms.TextInput(),
            "age": forms.NumberInput(),
            "gym_experience": forms.TextInput(
                attrs={
                    "placeholder": "misal: belum, cuma pernah beberapa kali, pernah rutin 6 bulan"
                }
            ),
            "know_mulai_gym_from": forms.TextInput(
                attrs={
                    "placeholder": "misal: ngelewat, instagram, tiktok, teman, google maps, ..."
                }
            ),
            "social_media_username": forms.TextInput(
                attrs={"placeholder": "Username Instagram/TikTok"}
            ),
            "visit_schedule": forms.TextInput(
                attrs={
                    "placeholder": "misal: 19 Juli siang jam 12, 20 Juli sore jam 3, ..."
                }
            ),
        }
