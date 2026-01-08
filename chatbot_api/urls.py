from django.urls import path
from . import views

app_name = "chatbot_api"

urlpatterns = [
    path("classes/", views.get_classes, name="classes"),
    path("member/", views.get_member, name="member"),
    path("book/", views.book_class, name="book"),
    path("waitlist/", views.join_waitlist, name="waitlist"),
    path("cancel/", views.cancel_booking, name="cancel"),
    path("my-bookings/", views.get_my_bookings, name="my_bookings"),
]
