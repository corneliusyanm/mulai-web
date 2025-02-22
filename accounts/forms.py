from django import forms
from .models import Member

class MemberSignUpForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'name', 'email', 'phone_number',
            'gender', 'age', 'height', 'weight', 'years_of_working_out',
            'goals', 'know_mulai_gym_from'
        ]
        widgets = {
            'goals': forms.Textarea(attrs={'rows': 3}),
        }

class MemberLoginForm(forms.Form):
    email = forms.EmailField(label='Email') 