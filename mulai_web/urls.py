"""
URL configuration for mulai_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

import visits.admin_init  # Add this import
from visits.admin import admin_site  # Import the custom admin site
from visits import views as visit_views

from accounts.views import home, job_openings as lowongan_kerja, tamu_signup_view

urlpatterns = [
    # Use custom admin site instead of default
    path("admin/", admin_site.urls),
    path("daftar-grand-opening/", include("grand_opening.urls")),
    path("check-in/", visit_views.check_in_page, name="check_in_page"),
    path("check-out/", visit_views.check_out_page, name="check_out_page"),
    path("tamu/", tamu_signup_view, name="tamu_signup"),
    path("forget-member/", visit_views.forget_member, name="forget_member"),
    path("", home, name="home"),
    path("lowongan-kerja/", lowongan_kerja, name="lowongan_kerja"),
    path("accounts/", include("accounts.urls")),
    path("visits/", include("visits.urls")),
    path("alat/", include("equipment.urls", namespace="equipment")),
    # Redirect /kuesioner to Google Form
    path(
        "kuesioner/",
        RedirectView.as_view(
            url="https://docs.google.com/forms/d/e/1FAIpQLSdilwD3u1paDqWNSasgA4a-kBYI9SO6UqWhd06bHOyRqAKsVw/viewform?usp=header",
            permanent=False,
        ),
        name="kuesioner",
    ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
