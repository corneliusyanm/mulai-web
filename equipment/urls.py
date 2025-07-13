from django.urls import path
from . import views

app_name = "equipment"

urlpatterns = [
    path("", views.equipment_list, name="list"),
    path("<slug:slug>/", views.equipment_detail, name="detail"),
]
