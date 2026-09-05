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
    path("nilai/<int:instance_id>/", views.class_review, name="class_review"),
    path("nilai/<int:instance_id>/tap/", views.rate_class, name="rate_class"),
    path(
        "nilai/<int:instance_id>/lewati/",
        views.skip_class_review,
        name="skip_class_review",
    ),
]
