from django import forms

from .models import Member


class MemberSignUpForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "name",
            "email",
            "phone_number",
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


class MemberLoginForm(forms.Form):
    email = forms.EmailField(label="Email")


class MemberEditForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "name",
            "phone_number",
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
