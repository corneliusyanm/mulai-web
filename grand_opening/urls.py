from django.urls import path
from . import views

app_name = "grand_opening"

urlpatterns = [
    path("", views.signup_view, name="signup"),
    path("sukses/", views.success_view, name="signup_success"),
]
