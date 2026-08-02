from django.urls import path

from . import views

app_name = "nutrition"

urlpatterns = [
    path("", views.index, name="index"),
    # Before the chapter pattern, or "harian" would be read as a chapter slug.
    path("harian/", views.daily, name="daily"),
    path("harian/jawab/", views.daily_answer, name="daily_answer"),
    path("<slug:slug>/", views.chapter, name="chapter"),
    path("<slug:slug>/selesai/", views.finish, name="finish"),
]
