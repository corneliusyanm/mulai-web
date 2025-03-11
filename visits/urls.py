from django.urls import path

from . import views

urlpatterns = [
    path(
        'check-in/',
        views.check_in_page,
        name='check_in_page'),
    path(
        'check-in/success/',
        views.check_in_success,
        name='check_in_success'),
    path(
        'check-out/',
        views.check_out_page,
        name='check_out_page'),
    path(
        'check-out/success/',
        views.check_out_success,
        name='check_out_success'),
    path(
        'forget-member/',
        views.forget_member,
        name='forget_member'),
]
