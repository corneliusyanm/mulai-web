from django.urls import path

from . import views

app_name = "announcements"

urlpatterns = [
    path("aktif/", views.active_announcements, name="active"),
]
