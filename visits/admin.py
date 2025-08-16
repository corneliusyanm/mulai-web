from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import csv

from .models import Visit
from accounts.models import Member
from payments.models import Payment, Package


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
        path(
            "analytics/members-by-date/",
            members_by_date_view,
            name="members-by-date",
        ),
        path(
            "analytics/member-details/<int:member_id>/",
            member_details_view,
            name="member-details",
        ),
        path(
            "analytics/export-members/",
            export_members_view,
            name="export-members",
        ),
    ]


admin_site.get_urls = lambda: get_custom_admin_urls() + admin_site.__class__.get_urls(
    admin_site
)


def membership_analytics_view(request):
    """Enhanced membership analytics dashboard"""
    if not request.user.is_staff:
        raise PermissionDenied

    # Get date range from request or default to 52 weeks
    weeks_ahead = int(request.GET.get("weeks", 52))
    start_date = request.GET.get("start_date")

    if start_date:
        try:
            today = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            today = timezone.now().date()
    else:
        today = timezone.now().date()

    # Calculate weekly projections
    weeks_data = []
    for week_num in range(weeks_ahead):
        week_end = today + timedelta(days=(week_num + 1) * 7 - today.weekday() - 1)
        week_end_datetime = timezone.make_aware(
            timezone.datetime.combine(week_end, timezone.datetime.min.time())
        )

        active_count = Member.objects.filter(
            active_until__gte=week_end_datetime
        ).count()
        pemula_count = Member.objects.filter(
            pemula_active_until__gte=week_end_datetime
        ).count()
        semi_private_count = Member.objects.filter(
            semi_private_active_until__gte=week_end_datetime
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

    # Calculate smart alerts and insights
    alerts = calculate_smart_alerts()
    insights = calculate_business_insights()
    revenue_projections = calculate_revenue_projections(weeks_data)

    # Current membership stats
    now = timezone.now()
    current_stats = {
        "total_members": Member.objects.count(),
        "active_members": Member.objects.filter(active_until__gte=now).count(),
        "pemula_active": Member.objects.filter(pemula_active_until__gte=now).count(),
        "semi_private_active": Member.objects.filter(
            semi_private_active_until__gte=now
        ).count(),
        "pt_active": Member.objects.filter(pt_session_count__gt=0).count(),
    }

    context = {
        **admin_site.each_context(request),
        "title": "Advanced Membership Analytics",
        "weeks_data": json.dumps(weeks_data),
        "weeks_count": len(weeks_data),
        "alerts": alerts,
        "insights": insights,
        "revenue_projections": revenue_projections,
        "current_stats": current_stats,
        "weeks_ahead": weeks_ahead,
        "start_date": today.strftime("%Y-%m-%d"),
    }

    return render(request, "admin/analytics/membership_projections.html", context)


def calculate_smart_alerts():
    """Calculate smart alerts for business insights"""
    alerts = []
    now = timezone.now()

    # Members expiring soon
    expiring_7_days = Member.objects.filter(
        active_until__gte=now, active_until__lte=now + timedelta(days=7)
    ).count()

    expiring_14_days = Member.objects.filter(
        active_until__gte=now, active_until__lte=now + timedelta(days=14)
    ).count()

    expiring_30_days = Member.objects.filter(
        active_until__gte=now, active_until__lte=now + timedelta(days=30)
    ).count()

    if expiring_7_days > 0:
        alerts.append(
            {
                "type": "warning",
                "title": f"{expiring_7_days} Member(s) Expiring This Week",
                "message": "Consider reaching out for renewals",
                "action_url": "/admin/accounts/member/?active_until__gte="
                + now.strftime("%Y-%m-%d")
                + "&active_until__lte="
                + (now + timedelta(days=7)).strftime("%Y-%m-%d"),
            }
        )

    if expiring_30_days > 10:
        alerts.append(
            {
                "type": "info",
                "title": f"{expiring_30_days} Members Expiring This Month",
                "message": "Plan retention campaigns",
                "action_url": "/admin/accounts/member/",
            }
        )

    # Low visit activity
    low_visit_members = (
        Member.objects.filter(active_until__gte=now)
        .exclude(visit__check_in_time__gte=now - timedelta(days=14))
        .count()
    )

    if low_visit_members > 0:
        alerts.append(
            {
                "type": "info",
                "title": f"{low_visit_members} Active Members Haven't Visited Recently",
                "message": "Consider follow-up for engagement",
                "action_url": "/admin/reminders/reminder/",
            }
        )

    return alerts


def calculate_business_insights():
    """Calculate business insights and trends"""
    now = timezone.now()

    # Membership growth trend (last 3 months)
    three_months_ago = now - relativedelta(months=3)
    new_members_3m = Member.objects.filter(created_at__gte=three_months_ago).count()

    # Revenue trend
    payments_3m = Payment.objects.filter(payment_date__gte=three_months_ago)
    total_revenue_3m = payments_3m.aggregate(total=Sum("amount"))["total"] or 0

    # Average membership duration
    completed_memberships = Member.objects.filter(
        active_until__lt=now, created_at__gte=now - relativedelta(months=12)
    )

    insights = {
        "new_members_3m": new_members_3m,
        "total_revenue_3m": float(total_revenue_3m),
        "avg_monthly_signups": round(new_members_3m / 3, 1),
        "avg_monthly_revenue": round(float(total_revenue_3m) / 3, 2),
    }

    return insights


def calculate_revenue_projections(weeks_data):
    """Calculate revenue projections based on membership data"""
    # Get average package prices
    try:
        avg_package_price = (
            Package.objects.aggregate(avg_price=Sum("default_price"))["avg_price"] or 0
        )

        # Simple projection: active members * average monthly fee
        projections = []
        for week in weeks_data[:12]:  # Next 12 weeks
            estimated_revenue = week["active_count"] * (
                float(avg_package_price) / 4
            )  # Weekly estimate
            projections.append(
                {"week": week["week_label"], "revenue": round(estimated_revenue, 2)}
            )

        return projections
    except:
        return []


def members_by_date_view(request):
    """AJAX view to get members active on a specific date"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    date_str = request.GET.get("date")
    membership_type = request.GET.get("type", "active")

    if not date_str:
        return JsonResponse({"error": "Date parameter required"}, status=400)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        target_datetime = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.max.time())
        )

        # Filter members based on membership type
        if membership_type == "pemula":
            members = Member.objects.filter(pemula_active_until__gte=target_datetime)
        elif membership_type == "semi_private":
            members = Member.objects.filter(
                semi_private_active_until__gte=target_datetime
            )
        else:  # default to 'active'
            members = Member.objects.filter(active_until__gte=target_datetime)

        members_data = []
        for member in members:
            # Get expiry date for the specific membership type
            if membership_type == "pemula":
                expiry = member.pemula_active_until
            elif membership_type == "semi_private":
                expiry = member.semi_private_active_until
            else:
                expiry = member.active_until

            members_data.append(
                {
                    "id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "phone": member.phone_number,
                    "expiry_date": expiry.strftime("%Y-%m-%d %H:%M") if expiry else "",
                    "whatsapp_link": f"https://wa.me/{member.phone_number}",
                }
            )

        return JsonResponse(
            {
                "members": members_data,
                "count": len(members_data),
                "date": date_str,
                "type": membership_type,
            }
        )

    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)


def member_details_view(request, member_id):
    """AJAX view to get detailed member information"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    member = get_object_or_404(Member, id=member_id)

    # Get recent payments
    recent_payments = Payment.objects.filter(member=member).order_by("-payment_date")[
        :5
    ]
    payments_data = [
        {
            "date": payment.payment_date.strftime("%Y-%m-%d"),
            "amount": float(payment.amount),
            "package": payment.package.description if payment.package else "N/A",
        }
        for payment in recent_payments
    ]

    # Get recent visits
    recent_visits = Visit.objects.filter(member=member).order_by("-check_in_time")[:10]
    visits_data = [
        {
            "check_in": visit.check_in_time.strftime("%Y-%m-%d %H:%M"),
            "check_out": (
                visit.check_out_time.strftime("%Y-%m-%d %H:%M")
                if visit.check_out_time
                else "Still visiting"
            ),
        }
        for visit in recent_visits
    ]

    member_data = {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "phone": member.phone_number,
        "age": member.age,
        "gender": member.get_gender_display(),
        "created_at": member.created_at.strftime("%Y-%m-%d"),
        "active_until": (
            member.active_until.strftime("%Y-%m-%d %H:%M")
            if member.active_until
            else ""
        ),
        "pemula_active_until": (
            member.pemula_active_until.strftime("%Y-%m-%d %H:%M")
            if member.pemula_active_until
            else ""
        ),
        "semi_private_active_until": (
            member.semi_private_active_until.strftime("%Y-%m-%d %H:%M")
            if member.semi_private_active_until
            else ""
        ),
        "pt_session_count": member.pt_session_count,
        "is_active": member.is_active_member,
        "whatsapp_link": f"https://wa.me/{member.phone_number}",
        "recent_payments": payments_data,
        "recent_visits": visits_data,
    }

    return JsonResponse({"member": member_data})


def export_members_view(request):
    """Export members data to CSV"""
    if not request.user.is_staff:
        raise PermissionDenied

    date_str = request.GET.get("date")
    membership_type = request.GET.get("type", "active")

    # Create CSV response
    response = HttpResponse(content_type="text/csv")
    filename = f"members_{membership_type}_{date_str or 'all'}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Phone", "Expiry Date", "Created Date", "Status"])

    # Get members based on filters
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            target_datetime = timezone.make_aware(
                timezone.datetime.combine(target_date, timezone.datetime.max.time())
            )

            if membership_type == "pemula":
                members = Member.objects.filter(
                    pemula_active_until__gte=target_datetime
                )
            elif membership_type == "semi_private":
                members = Member.objects.filter(
                    semi_private_active_until__gte=target_datetime
                )
            else:
                members = Member.objects.filter(active_until__gte=target_datetime)
        except ValueError:
            members = Member.objects.all()
    else:
        members = Member.objects.all()

    for member in members:
        if membership_type == "pemula":
            expiry = member.pemula_active_until
        elif membership_type == "semi_private":
            expiry = member.semi_private_active_until
        else:
            expiry = member.active_until

        writer.writerow(
            [
                member.name,
                member.email,
                member.phone_number,
                expiry.strftime("%Y-%m-%d %H:%M") if expiry else "",
                member.created_at.strftime("%Y-%m-%d"),
                "Active" if (expiry and expiry >= timezone.now()) else "Inactive",
            ]
        )

    return response


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
    autocomplete_fields = ["member"]
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
