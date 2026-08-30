from django.urls import path
from . import views

app_name = "classes"

urlpatterns = [
    path("", views.ClassListView.as_view(), name="class_list"),
    path("aturan/", views.class_rules, name="class_rules"),
    path("<int:pk>/", views.ClassDetailView.as_view(), name="class_detail"),
    path("book/<int:instance_id>/", views.book_class, name="book_class"),
    path("cancel/<int:instance_id>/", views.cancel_class, name="cancel_class"),
    path(
        "<int:instance_id>/kalender/", views.class_calendar, name="class_calendar"
    ),
]
