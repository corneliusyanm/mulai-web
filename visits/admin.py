from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import json

from .models import Visit
from accounts.models import Member


class CustomAdminSite(admin.AdminSite):
    site_header = "Mulai Gym Admin"
    site_title = "Mulai Gym Admin"
    index_title = "Home"

    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)

        # Add Quick Access section only on the main admin page
        if app_label is None:
            # Update for visits app
            visit_app = next(
                (app for app in app_list if app["app_label"] == "visits"), None
            )
            if visit_app:
                visit_app["models"].extend(
                    [
                        {
                            "name": "Currently Visiting",
                            "object_name": "Currently Visiting",
                            "admin_url": reverse("admin:current-visits"),
                            "view_only": True,
                            "perms": {"view": True},
                        },
                        {
                            "name": "Visit History",
                            "object_name": "Visit History",
                            "admin_url": reverse("admin:visit-history"),
                            "view_only": True,
                            "perms": {"view": True},
                        },
                    ]
                )

            # Update for reminders app
            reminder_app = next(
                (app for app in app_list if app["app_label"] == "reminders"), None
            )
            if reminder_app:
                reminder_app["models"].extend(
                    [
                        {
                            "name": "Current Reminders",
                            "object_name": "Current Reminders",
                            "admin_url": reverse("admin:current-reminders"),
                            "view_only": True,
                            "perms": {"view": True},
                        },
                        {
                            "name": "Reminder History",
                            "object_name": "Reminder History",
                            "admin_url": reverse("admin:reminder-history"),
                            "view_only": True,
                            "perms": {"view": True},
                        },
                    ]
                )

            # Add Analytics section
            analytics_app = {
                "name": "Analytics",
                "app_label": "analytics",
                "app_url": None,
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Membership Projections",
                        "object_name": "Membership Projections",
                        "admin_url": reverse("admin:membership-analytics"),
                        "view_only": True,
                        "perms": {"view": True},
                    },
                ],
            }
            app_list.append(analytics_app)

        return app_list


# Create an instance of the custom admin site
admin_site = CustomAdminSite(name="custom_admin")


# Add custom URLs to admin site
def get_custom_admin_urls():
    return [
        path(
            "analytics/membership/",
            membership_analytics_view,
            name="membership-analytics",
        ),
    ]


admin_site.get_urls = lambda: get_custom_admin_urls() + admin_site.__class__.get_urls(
    admin_site
)


def membership_analytics_view(request):
    """View for membership analytics dashboard"""
    if not request.user.is_staff:
        raise PermissionDenied

    # Calculate weekly projections for next 52 weeks
    today = timezone.now().date()
    weeks_data = []

    for week_num in range(52):
        # Calculate the end of each week (Saturday)
        week_end = today + timedelta(days=(week_num + 1) * 7 - today.weekday() - 1)

        # Count members who will still be active by end of this week
        active_count = Member.objects.filter(
            active_until__gte=timezone.make_aware(
                timezone.datetime.combine(week_end, timezone.datetime.min.time())
            )
        ).count()

        pemula_count = Member.objects.filter(
            pemula_active_until__gte=timezone.make_aware(
                timezone.datetime.combine(week_end, timezone.datetime.min.time())
            )
        ).count()

        semi_private_count = Member.objects.filter(
            semi_private_active_until__gte=timezone.make_aware(
                timezone.datetime.combine(week_end, timezone.datetime.min.time())
            )
        ).count()

        weeks_data.append(
            {
                "week_end": week_end.strftime("%Y-%m-%d"),
                "week_label": week_end.strftime("%d %b"),
                "active_count": active_count,
                "pemula_count": pemula_count,
                "semi_private_count": semi_private_count,
            }
        )

    context = {
        **admin_site.each_context(request),
        "title": "Membership Analytics",
        "weeks_data": json.dumps(weeks_data),
        "weeks_count": len(weeks_data),
    }

    return render(request, "admin/analytics/membership_projections.html", context)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "formatted_check_in",
        "formatted_check_out",
        "visit_status",
    )
    list_filter = (
        ("check_in_time", DateFieldListFilter),
        ("check_out_time", DateFieldListFilter),
    )
    search_fields = ("member__name", "member__email", "member__phone_number")
    change_list_template = "admin/visits/visit/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("current/", self.current_visits_view, name="current-visits"),
            path("history/", self.visit_history_view, name="visit-history"),
            path(
                "checkout/<int:visit_id>/", self.checkout_visit, name="checkout-visit"
            ),
            path("delete/<int:visit_id>/", self.delete_visit, name="delete-visit"),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        # Show most recent visits first
        return super().get_queryset(request).order_by("-check_in_time")

    def formatted_check_in(self, obj):
        return timezone.localtime(obj.check_in_time).strftime("%d %b %Y %H:%M")

    formatted_check_in.short_description = "Check In Time"

    def formatted_check_out(self, obj):
        if obj.check_out_time:
            return timezone.localtime(obj.check_out_time).strftime("%d %b %Y %H:%M")
        return "-"

    formatted_check_out.short_description = "Check Out Time"

    def visit_status(self, obj):
        if not obj.check_out_time:
            return "Currently Visiting"
        return "Completed"

    visit_status.short_description = "Status"

    def checkout_visit(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id)
            if not visit.check_out_time:
                visit.check_out_time = timezone.now()
                visit.save()
                messages.success(
                    request, f"Successfully checked out {visit.member.name}"
                )
            else:
                messages.warning(request, "Kunjungan sudah check-out")
        except Visit.DoesNotExist:
            messages.error(request, "Kunjungan tidak ditemukan")
        return redirect("admin:current-visits")

    def delete_visit(self, request, visit_id):
        if not self.has_delete_permission(request):
            raise PermissionDenied

        redirect_to = "admin:current-visits"
        if request.GET.get("from") == "history":
            redirect_to = "admin:visit-history"

        try:
            visit = Visit.objects.get(id=visit_id)
            # Check object-level permission
            if not self.has_delete_permission(request, visit):
                raise PermissionDenied

            member_name = visit.member.name
            visit.delete()
            messages.success(request, f"Successfully deleted visit for {member_name}")
        except Visit.DoesNotExist:
            messages.error(request, "Kunjungan tidak ditemukan")
        return redirect(redirect_to)

    def current_visits_view(self, request):
        visits = Visit.objects.filter(check_out_time__isnull=True).order_by(
            "-check_in_time"
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Currently Visiting Members",
            "visits": visits,
            "opts": self.model._meta,
            "current_view": "current",
            "has_change_permission": self.has_change_permission(request),
            "has_delete_permission": self.has_delete_permission(request),
        }
        return render(request, "admin/visits/visit/current_visits.html", context)

    def visit_history_view(self, request):
        # Get completed visits (has check-out time)
        visits = Visit.objects.filter(check_out_time__isnull=False).order_by(
            "-check_in_time"
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Visit History",
            "visits": visits,
            "opts": self.model._meta,
            "current_view": "history",
            "has_change_permission": self.has_change_permission(request),
            "has_delete_permission": self.has_delete_permission(request),
        }
        return render(request, "admin/visits/visit/visit_history.html", context)


# Register the models with the custom admin site
admin_site.register(Visit, VisitAdmin)
