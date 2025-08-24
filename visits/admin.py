from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count, Q, Sum, Avg, F, Case, When, IntegerField, FloatField
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import csv
from decimal import Decimal

from .models import Visit
from accounts.models import Member
from payments.models import Payment, Package
from purchases.models import Sale, Product, SaleItem


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal, date, and datetime objects"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "strftime"):  # datetime or date objects
            return obj.strftime("%Y-%m-%d")
        elif hasattr(obj, "total_seconds"):  # timedelta objects
            return obj.total_seconds() / 3600  # Convert to hours
        return super().default(obj)


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
                    {
                        "name": "Business Intelligence",
                        "object_name": "Business Intelligence",
                        "admin_url": reverse("admin:business-analytics"),
                        "view_only": True,
                        "perms": {"view": True},
                    },
                    {
                        "name": "Weekly Metrics Tracker",
                        "object_name": "Weekly Metrics Tracker",
                        "admin_url": reverse("admin:weekly-metrics"),
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
            "analytics/business/",
            business_analytics_view,
            name="business-analytics",
        ),
        path(
            "analytics/weekly-metrics/",
            weekly_metrics_view,
            name="weekly-metrics",
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
        path(
            "analytics/revenue-data/",
            revenue_data_view,
            name="revenue-data",
        ),
        path(
            "analytics/sales-data/",
            sales_data_view,
            name="sales-data",
        ),
        path(
            "analytics/visits-data/",
            visits_data_view,
            name="visits-data",
        ),
        path(
            "analytics/export-business/",
            export_business_data_view,
            name="export-business",
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


def business_analytics_view(request):
    """Comprehensive business intelligence dashboard"""
    if not request.user.is_staff:
        raise PermissionDenied

    # Get date range from request with new period types
    period_type = request.GET.get("period_type", "7_days")
    analysis_type = request.GET.get("type", "overview")

    now = timezone.now()

    # Handle custom date range
    if period_type == "custom":
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            # Default to last 8 weeks if custom dates not provided
            start_date = now - timedelta(days=7)
            end_date = now
    else:
        # Handle predefined period types
        end_date = now
        if period_type == "7_days":
            start_date = now - timedelta(days=7)
        elif period_type == "2_weeks":
            start_date = now - timedelta(weeks=2)
        elif period_type == "4_weeks":
            start_date = now - timedelta(weeks=4)
        elif period_type == "8_weeks":
            start_date = now - timedelta(weeks=8)
        elif period_type == "3_months":
            start_date = now - relativedelta(months=3)
        elif period_type == "6_months":
            start_date = now - relativedelta(months=6)
        else:
            # Default to 8 weeks
            start_date = now - timedelta(weeks=8)

    # Calculate comprehensive business metrics
    business_metrics = calculate_business_metrics(start_date, end_date)
    revenue_analytics = calculate_revenue_analytics(start_date, end_date)
    sales_analytics = calculate_sales_analytics(start_date, end_date)
    visit_analytics = calculate_visit_analytics(start_date, end_date)
    member_analytics = calculate_member_analytics(start_date, end_date)
    repurchase_analytics = calculate_repurchase_analytics(start_date, end_date)

    context = {
        **admin_site.each_context(request),
        "title": "Business Intelligence Dashboard",
        "business_metrics": business_metrics,
        "revenue_analytics": json.dumps(revenue_analytics, cls=DecimalEncoder),
        "sales_analytics": json.dumps(sales_analytics, cls=DecimalEncoder),
        "visit_analytics": json.dumps(visit_analytics, cls=DecimalEncoder),
        "member_analytics": json.dumps(member_analytics, cls=DecimalEncoder),
        "repurchase_analytics": repurchase_analytics,
        "period_type": period_type,
        "analysis_type": analysis_type,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }

    return render(request, "admin/analytics/business_intelligence.html", context)


def weekly_metrics_view(request):
    """Weekly metrics dashboard for repurchase rates"""
    if not request.user.is_staff:
        raise PermissionDenied

    today = timezone.now().date()
    end_date_str = request.GET.get("end_date", today.strftime("%Y-%m-%d"))
    start_date_str = request.GET.get(
        "start_date", (today - timedelta(days=6)).strftime("%Y-%m-%d")
    )

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        # Handle invalid date format
        start_date = today - timedelta(days=6)
        end_date = today

    # Logic to get repurchase data
    # Step 1: Find members whose membership expires in the selected week
    expiring_members = Member.objects.filter(
        active_until__date__gte=start_date, active_until__date__lte=end_date
    ).distinct()

    # Step 1.5: Filter to only include members who have EVER purchased actual membership packages (non-"-0")
    # This excludes members who only ever bought single-visit passes
    actual_members = (
        expiring_members.filter(payment__package__code__isnull=False)
        .exclude(payment__package__code__endswith="-0")
        .distinct()
    )

    repurchased_members_info = []
    did_not_repurchase_members = []

    # Step 2: For each actual member (who had real memberships), check if they made any payment in the same week
    repurchased_member_ids = set()

    for member in actual_members:
        # Check if this member made any payment during the week
        # EXCLUDE *-0 packages (per visit only, not membership renewals)
        member_payments = Payment.objects.filter(
            member=member,
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
        ).select_related("package")

        # Filter out *-0 packages (per visit packages)
        membership_payments = member_payments.exclude(package__code__endswith="-0")

        if membership_payments.exists():
            # Member repurchased - add to repurchased list
            repurchased_member_ids.add(member.id)

            # Add all their MEMBERSHIP payments in this period to the info list
            for payment in membership_payments:
                repurchased_members_info.append(
                    {
                        "member": payment.member,
                        "payment_date": payment.payment_date,
                        "amount": payment.amount,
                        "package_code": (
                            payment.package.code if payment.package else "N/A"
                        ),
                        "notes": payment.notes,
                    }
                )

    # Step 3: Members who didn't repurchase
    did_not_repurchase_members = actual_members.exclude(id__in=repurchased_member_ids)

    total_expiring = actual_members.count()
    total_repurchased = len(repurchased_member_ids)

    repurchase_rate = (
        (total_repurchased / total_expiring) * 100 if total_expiring > 0 else 0
    )

    context = {
        **admin_site.each_context(request),
        "title": "Weekly Metrics Tracker",
        "start_date": start_date,
        "end_date": end_date,
        "repurchase_rate": repurchase_rate,
        "total_expiring": total_expiring,
        "total_repurchased": total_repurchased,
        "repurchased_members": repurchased_members_info,
        "did_not_repurchase_members": did_not_repurchase_members,
    }

    return render(request, "admin/analytics/weekly_metrics.html", context)


def calculate_business_metrics(start_date, end_date):
    """Calculate key business performance indicators"""

    # Revenue metrics
    total_revenue = (
        Payment.objects.filter(
            payment_date__gte=start_date, payment_date__lte=end_date
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    store_revenue = (
        Sale.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    # Member metrics
    total_members = Member.objects.count()
    new_members = Member.objects.filter(created_at__gte=start_date).count()
    active_members = Member.objects.filter(active_until__gte=end_date).count()

    # Visit metrics
    total_visits = Visit.objects.filter(check_in_time__gte=start_date).count()
    unique_visitors = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .values("member")
        .distinct()
        .count()
    )

    # Average metrics
    avg_visit_duration = Visit.objects.filter(
        check_in_time__gte=start_date, check_out_time__isnull=False
    ).aggregate(avg_duration=Avg(F("check_out_time") - F("check_in_time")))[
        "avg_duration"
    ]

    avg_revenue_per_member = float(total_revenue) / max(new_members, 1)

    # Customer lifetime value estimation
    if active_members > 0:
        avg_payment = (
            Payment.objects.filter(payment_date__gte=start_date).aggregate(
                avg=Avg("amount")
            )["avg"]
            or 0
        )

        # Estimate based on average payment frequency
        payment_frequency = Payment.objects.filter(
            payment_date__gte=start_date
        ).count() / max(active_members, 1)

        customer_lifetime_value = (
            float(avg_payment) * payment_frequency * 12
        )  # Annual estimate
    else:
        customer_lifetime_value = 0

    return {
        "total_revenue": float(total_revenue),
        "store_revenue": float(store_revenue),
        "membership_revenue": float(total_revenue),
        "total_members": total_members,
        "new_members": new_members,
        "active_members": active_members,
        "total_visits": total_visits,
        "unique_visitors": unique_visitors,
        "avg_visit_duration": (
            avg_visit_duration.total_seconds() / 3600 if avg_visit_duration else 0
        ),  # in hours
        "avg_revenue_per_member": avg_revenue_per_member,
        "customer_lifetime_value": customer_lifetime_value,
        "member_retention_rate": (active_members / max(total_members, 1)) * 100,
    }


def calculate_revenue_analytics(start_date, end_date):
    """Calculate detailed revenue analytics"""

    # Monthly revenue trend
    monthly_data = []
    current_date = start_date.replace(day=1)

    while current_date <= end_date:
        next_month = current_date + relativedelta(months=1)

        membership_revenue = (
            Payment.objects.filter(
                payment_date__gte=current_date, payment_date__lt=next_month
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        store_revenue = (
            Sale.objects.filter(
                created_at__gte=current_date, created_at__lt=next_month
            ).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )

        monthly_data.append(
            {
                "month": current_date.strftime("%Y-%m"),
                "month_label": current_date.strftime("%b %Y"),
                "membership_revenue": float(membership_revenue),
                "store_revenue": float(store_revenue),
                "total_revenue": float(membership_revenue + store_revenue),
            }
        )

        current_date = next_month

    # Revenue by payment method
    payment_methods = (
        Payment.objects.filter(payment_date__gte=start_date)
        .values("payment_method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    # Convert Decimal values to float for JSON serialization
    payment_methods = [
        {**item, "total": float(item["total"]) if item["total"] else 0}
        for item in payment_methods
    ]

    # Revenue by package
    package_revenue = (
        Payment.objects.filter(payment_date__gte=start_date, package__isnull=False)
        .values("package__code", "package__description")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    # Convert Decimal values to float for JSON serialization
    package_revenue = [
        {**item, "total": float(item["total"]) if item["total"] else 0}
        for item in package_revenue
    ]

    return {
        "monthly_trends": monthly_data,
        "payment_methods": payment_methods,
        "package_revenue": package_revenue,
    }


def calculate_sales_analytics(start_date, end_date):
    """Calculate store sales analytics"""

    # Top selling products
    top_products = (
        SaleItem.objects.filter(sale__created_at__gte=start_date)
        .values("product__name")
        .annotate(
            quantity_sold=Sum("quantity"),
            total_revenue=Sum(F("quantity") * F("price_at_purchase")),
            transaction_count=Count("sale", distinct=True),
        )
        .order_by("-total_revenue")[:10]
    )

    # Convert Decimal values to float for JSON serialization
    top_products = [
        {
            **item,
            "total_revenue": (
                float(item["total_revenue"]) if item["total_revenue"] else 0
            ),
        }
        for item in top_products
    ]

    # Daily sales trend
    daily_sales = (
        Sale.objects.filter(created_at__gte=start_date)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(
            total_sales=Sum("total_amount"),
            transaction_count=Count("id"),
            avg_transaction=Avg("total_amount"),
        )
        .order_by("day")
    )

    # Convert Decimal values to float and date to string for JSON serialization
    daily_sales = [
        {
            **item,
            "day": (
                item["day"].strftime("%Y-%m-%d")
                if hasattr(item["day"], "strftime")
                else str(item["day"])
            ),
            "total_sales": float(item["total_sales"]) if item["total_sales"] else 0,
            "avg_transaction": (
                float(item["avg_transaction"]) if item["avg_transaction"] else 0
            ),
        }
        for item in daily_sales
    ]

    # Sales by payment method
    sales_payment_methods = (
        Sale.objects.filter(created_at__gte=start_date)
        .values("payment_method")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("-total")
    )

    # Convert Decimal values to float for JSON serialization
    sales_payment_methods = [
        {**item, "total": float(item["total"]) if item["total"] else 0}
        for item in sales_payment_methods
    ]

    return {
        "top_products": top_products,
        "daily_trends": daily_sales,
        "payment_methods": sales_payment_methods,
    }


def calculate_visit_analytics(start_date, end_date):
    """Calculate visit patterns and member engagement"""

    # Daily visit patterns
    daily_visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(select={"day": "date(check_in_time)"})
        .values("day")
        .annotate(
            total_visits=Count("id"), unique_members=Count("member", distinct=True)
        )
        .order_by("day")
    )

    # Hourly patterns
    hourly_visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(select={"hour": "extract(hour from check_in_time)"})
        .values("hour")
        .annotate(total_visits=Count("id"))
        .order_by("hour")
    )

    # Member visit frequency
    member_frequencies = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .values("member")
        .annotate(visit_count=Count("id"))
        .values("visit_count")
        .annotate(member_count=Count("member"))
        .order_by("visit_count")
    )

    # Average session duration
    avg_duration_by_day = (
        Visit.objects.filter(
            check_in_time__gte=start_date, check_out_time__isnull=False
        )
        .extra(select={"day": "date(check_in_time)"})
        .values("day")
        .annotate(avg_duration=Avg(F("check_out_time") - F("check_in_time")))
        .order_by("day")
    )

    # Convert date objects to strings for JSON serialization
    daily_visits_list = [
        {
            **item,
            "day": (
                item["day"].strftime("%Y-%m-%d")
                if hasattr(item["day"], "strftime")
                else str(item["day"])
            ),
        }
        for item in daily_visits
    ]

    session_durations_list = [
        {
            **item,
            "day": (
                item["day"].strftime("%Y-%m-%d")
                if hasattr(item["day"], "strftime")
                else str(item["day"])
            ),
            "avg_duration": (
                item["avg_duration"].total_seconds() / 3600
                if item["avg_duration"]
                else 0
            ),
        }
        for item in avg_duration_by_day
    ]

    return {
        "daily_visits": daily_visits_list,
        "hourly_patterns": list(hourly_visits),
        "member_frequencies": list(member_frequencies),
        "session_durations": session_durations_list,
    }


def calculate_member_analytics(start_date, end_date):
    """Calculate member acquisition and retention analytics"""

    # Member acquisition trend
    monthly_signups = (
        Member.objects.filter(created_at__gte=start_date)
        .extra(select={"month": "date_trunc('month', created_at)"})
        .values("month")
        .annotate(new_members=Count("id"))
        .order_by("month")
    )

    # Member segmentation by activity
    member_segments = []
    active_threshold = timezone.now() - timedelta(days=7)
    regular_threshold = timezone.now() - timedelta(days=30)

    # Highly active (visited in last 7 days)
    highly_active = (
        Member.objects.filter(visit__check_in_time__gte=active_threshold)
        .distinct()
        .count()
    )

    # Moderately active (visited in last 30 days but not last 7)
    moderately_active = (
        Member.objects.filter(
            visit__check_in_time__gte=regular_threshold,
            visit__check_in_time__lt=active_threshold,
        )
        .exclude(visit__check_in_time__gte=active_threshold)
        .distinct()
        .count()
    )

    # Inactive (haven't visited in 30+ days)
    inactive = Member.objects.exclude(
        visit__check_in_time__gte=regular_threshold
    ).count()

    member_segments = [
        {
            "segment": "Highly Active",
            "count": highly_active,
            "percentage": (highly_active / max(Member.objects.count(), 1)) * 100,
        },
        {
            "segment": "Moderately Active",
            "count": moderately_active,
            "percentage": (moderately_active / max(Member.objects.count(), 1)) * 100,
        },
        {
            "segment": "Inactive",
            "count": inactive,
            "percentage": (inactive / max(Member.objects.count(), 1)) * 100,
        },
    ]

    # Convert datetime objects to strings for JSON serialization
    monthly_signups_list = [
        {
            **item,
            "month": (
                item["month"].strftime("%Y-%m-%d")
                if hasattr(item["month"], "strftime")
                else str(item["month"])
            ),
        }
        for item in monthly_signups
    ]

    return {
        "monthly_signups": monthly_signups_list,
        "member_segments": member_segments,
    }


def calculate_repurchase_analytics(start_date, end_date):
    """Calculate customer lifetime value and repurchase behavior"""

    # Repurchase rate calculation
    members_with_payments = (
        Payment.objects.filter(payment_date__gte=start_date)
        .values("member")
        .distinct()
        .count()
    )

    members_with_multiple_payments = (
        Payment.objects.filter(payment_date__gte=start_date)
        .values("member")
        .annotate(payment_count=Count("id"))
        .filter(payment_count__gt=1)
        .count()
    )

    repurchase_rate = (
        members_with_multiple_payments / max(members_with_payments, 1)
    ) * 100

    # Average time between purchases
    member_payment_intervals = []
    for member in Member.objects.filter(
        payment__payment_date__gte=start_date
    ).distinct():
        payments = Payment.objects.filter(
            member=member, payment_date__gte=start_date
        ).order_by("payment_date")

        if payments.count() > 1:
            intervals = []
            for i in range(1, len(payments)):
                interval = (
                    payments[i].payment_date - payments[i - 1].payment_date
                ).days
                intervals.append(interval)

            if intervals:
                member_payment_intervals.extend(intervals)

    avg_repurchase_interval = (
        sum(member_payment_intervals) / len(member_payment_intervals)
        if member_payment_intervals
        else 0
    )

    # Customer lifetime value by cohort
    cohort_data = []
    for months_ago in range(6, 0, -1):  # Last 6 months cohorts
        cohort_start = timezone.now() - relativedelta(months=months_ago)
        cohort_end = cohort_start + relativedelta(months=1)

        cohort_members = Member.objects.filter(
            created_at__gte=cohort_start, created_at__lt=cohort_end
        )

        if cohort_members.exists():
            total_revenue = (
                Payment.objects.filter(
                    member__in=cohort_members, payment_date__gte=cohort_start
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            avg_clv = float(total_revenue) / cohort_members.count()

            cohort_data.append(
                {
                    "cohort": cohort_start.strftime("%b %Y"),
                    "members": cohort_members.count(),
                    "total_revenue": float(total_revenue),
                    "avg_clv": avg_clv,
                }
            )

    return {
        "repurchase_rate": repurchase_rate,
        "avg_repurchase_interval": avg_repurchase_interval,
        "cohort_analysis": cohort_data,
        "members_with_payments": members_with_payments,
        "repeat_customers": members_with_multiple_payments,
    }


def revenue_data_view(request):
    """AJAX endpoint for revenue data"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Handle new period types
    period_type = request.GET.get("period_type", "7_days")
    chart_type = request.GET.get("chart", "monthly")
    now = timezone.now()

    if period_type == "custom":
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            start_date = now - timedelta(days=7)
            end_date = now
    else:
        end_date = now
        if period_type == "7_days":
            start_date = now - timedelta(days=7)
        elif period_type == "2_weeks":
            start_date = now - timedelta(weeks=2)
        elif period_type == "4_weeks":
            start_date = now - timedelta(weeks=4)
        elif period_type == "8_weeks":
            start_date = now - timedelta(weeks=8)
        elif period_type == "3_months":
            start_date = now - relativedelta(months=3)
        elif period_type == "6_months":
            start_date = now - relativedelta(months=6)
        else:
            start_date = now - timedelta(days=7)

    if chart_type == "monthly":
        data = calculate_revenue_analytics(start_date, end_date)
        return JsonResponse(
            json.loads(json.dumps(data, cls=DecimalEncoder)), safe=False
        )
    elif chart_type == "weekly":
        # Calculate weekly data
        weekly_data = []
        current_date = start_date

        while current_date <= now:
            week_end = current_date + timedelta(days=7)

            revenue = (
                Payment.objects.filter(
                    payment_date__gte=current_date, payment_date__lt=week_end
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            weekly_data.append(
                {
                    "week": current_date.strftime("%Y-W%U"),
                    "week_label": current_date.strftime("%d %b"),
                    "revenue": float(revenue),
                }
            )

            current_date = week_end

        return JsonResponse({"weekly_trends": weekly_data})

    return JsonResponse({"error": "Invalid chart type"}, status=400)


def sales_data_view(request):
    """AJAX endpoint for sales data"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Handle new period types
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()

    if period_type == "custom":
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            start_date = now - timedelta(days=7)
            end_date = now
    else:
        end_date = now
        if period_type == "7_days":
            start_date = now - timedelta(days=7)
        elif period_type == "2_weeks":
            start_date = now - timedelta(weeks=2)
        elif period_type == "4_weeks":
            start_date = now - timedelta(weeks=4)
        elif period_type == "8_weeks":
            start_date = now - timedelta(weeks=8)
        elif period_type == "3_months":
            start_date = now - relativedelta(months=3)
        elif period_type == "6_months":
            start_date = now - relativedelta(months=6)
        else:
            start_date = now - timedelta(days=7)

    data = calculate_sales_analytics(start_date, end_date)
    return JsonResponse(data)


def visits_data_view(request):
    """AJAX endpoint for visit analytics"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Handle new period types
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()

    if period_type == "custom":
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            start_date = now - timedelta(days=7)
            end_date = now
    else:
        end_date = now
        if period_type == "7_days":
            start_date = now - timedelta(days=7)
        elif period_type == "2_weeks":
            start_date = now - timedelta(weeks=2)
        elif period_type == "4_weeks":
            start_date = now - timedelta(weeks=4)
        elif period_type == "8_weeks":
            start_date = now - timedelta(weeks=8)
        elif period_type == "3_months":
            start_date = now - relativedelta(months=3)
        elif period_type == "6_months":
            start_date = now - relativedelta(months=6)
        else:
            start_date = now - timedelta(days=7)

    data = calculate_visit_analytics(start_date, end_date)
    return JsonResponse(data)


def export_business_data_view(request):
    """Export comprehensive business analytics to CSV"""
    if not request.user.is_staff:
        raise PermissionDenied

    export_type = request.GET.get("type", "revenue")
    period_type = request.GET.get("period_type", "7_days")

    now = timezone.now()

    # Handle custom date range
    if period_type == "custom":
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            start_date = now - timedelta(days=7)
            end_date = now
    else:
        # Handle predefined period types
        end_date = now
        if period_type == "7_days":
            start_date = now - timedelta(days=7)
        elif period_type == "2_weeks":
            start_date = now - timedelta(weeks=2)
        elif period_type == "4_weeks":
            start_date = now - timedelta(weeks=4)
        elif period_type == "8_weeks":
            start_date = now - timedelta(weeks=8)
        elif period_type == "3_months":
            start_date = now - relativedelta(months=3)
        elif period_type == "6_months":
            start_date = now - relativedelta(months=6)
        else:
            start_date = now - timedelta(days=7)

    response = HttpResponse(content_type="text/csv")
    filename = f"business_analytics_{export_type}_{start_date.strftime('%Y%m%d')}_{now.strftime('%Y%m%d')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    if export_type == "revenue":
        writer.writerow(
            [
                "Date",
                "Membership Revenue",
                "Store Revenue",
                "Total Revenue",
                "Payment Method",
                "Package",
            ]
        )

        payments = Payment.objects.filter(payment_date__gte=start_date).select_related(
            "package"
        )
        for payment in payments:
            writer.writerow(
                [
                    payment.payment_date.strftime("%Y-%m-%d"),
                    payment.amount,
                    0,  # Store revenue
                    payment.amount,
                    payment.payment_method,
                    payment.package.code if payment.package else "N/A",
                ]
            )

        sales = Sale.objects.filter(created_at__gte=start_date)
        for sale in sales:
            writer.writerow(
                [
                    sale.created_at.strftime("%Y-%m-%d"),
                    0,  # Membership revenue
                    sale.total_amount,
                    sale.total_amount,
                    sale.payment_method,
                    "Store Sale",
                ]
            )

    elif export_type == "visits":
        writer.writerow(
            ["Date", "Member Name", "Check In", "Check Out", "Duration (hours)"]
        )

        visits = Visit.objects.filter(check_in_time__gte=start_date).select_related(
            "member"
        )
        for visit in visits:
            duration = 0
            if visit.check_out_time:
                duration = (
                    visit.check_out_time - visit.check_in_time
                ).total_seconds() / 3600

            writer.writerow(
                [
                    visit.check_in_time.strftime("%Y-%m-%d"),
                    visit.member.name,
                    visit.check_in_time.strftime("%H:%M"),
                    (
                        visit.check_out_time.strftime("%H:%M")
                        if visit.check_out_time
                        else "Still visiting"
                    ),
                    round(duration, 2),
                ]
            )

    return response


class VisitAdmin(admin.ModelAdmin):
    list_display = (
        "clickable_id",
        "clickable_member",
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

    def clickable_id(self, obj):
        """Clickable ID that links to the visit detail page"""
        url = reverse("admin:visits_visit_change", args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.id)

    clickable_id.short_description = "ID"
    clickable_id.admin_order_field = "id"

    def clickable_member(self, obj):
        """Clickable member name that links to the member detail page"""
        url = reverse("admin:accounts_member_change", args=[obj.member.id])
        return format_html('<a href="{}">{}</a>', url, obj.member.name)

    clickable_member.short_description = "Member"
    clickable_member.admin_order_field = "member__name"

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
