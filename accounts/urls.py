from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.MemberSignUpView.as_view(), name='signup'),
    path('signup/success/', views.signup_success, name='signup_success'),
    path('login/', views.member_login, name='member_login'),
    path('logout/', views.member_logout, name='member_logout'),
    path('account/', views.MemberDetailView.as_view(), name='member_details'),
]
