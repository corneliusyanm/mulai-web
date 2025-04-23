from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("daftar/", views.MemberSignUpView.as_view(), name="signup"),
    path("daftar/berhasil/", views.signup_success, name="signup_success"),
    path("masuk/", views.member_login, name="member_login"),
    path("keluar/", views.member_logout, name="member_logout"),
    path("akun/", views.MemberDetailView.as_view(), name="member_details"),
    path("akun/ubah/", views.MemberEditView.as_view(), name="member_edit"),
    path("lowongan-kerja/", views.job_openings, name="job_openings"),
]
