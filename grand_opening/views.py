from django.shortcuts import render, redirect
from .forms import GrandOpeningRegistrationForm


def signup_view(request):
    if request.method == "POST":
        form = GrandOpeningRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("grand_opening:signup_success")
    else:
        form = GrandOpeningRegistrationForm()
    return render(request, "grand_opening/signup.html", {"form": form})


def success_view(request):
    return render(request, "grand_opening/signup_success.html")
