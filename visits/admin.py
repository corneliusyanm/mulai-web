from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import (
    Count,
    Q,
    Sum,
    Avg,
    F,
    Case,
    When,
    IntegerField,
    FloatField,
)
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import csv
from decimal import Decimal

from .models import Visit
from accounts.models import Member, Tamu
from payments.models import Payment, Package
from purchases.models import Sale, Product, SaleItem
from equipment.models import Equipment


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
            "analytics/visits-by-duration/",
            visits_by_duration_view,
            name="visits-by-duration",
        ),
        path(
            "analytics/visits-by-frequency/",
            visits_by_frequency_view,
            name="visits-by-frequency",
        ),
        path(
            "analytics/visits-by-day/",
            visits_by_day_view,
            name="visits-by-day",
        ),
        path(
            "analytics/visits-by-hour/",
            visits_by_hour_view,
            name="visits-by-hour",
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
        "revenue_projections_json": json.dumps(revenue_projections),
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


def calculate_enhanced_kpis(business_metrics, repurchase_analytics):
    """Calculate enhanced KPI metrics for the BI dashboard"""

    # Safe division helper
    def safe_divide(numerator, denominator):
        return (numerator / denominator) if denominator > 0 else 0

    # Calculate enhanced KPIs
    member_activation_rate = (
        safe_divide(
            business_metrics.get("active_members", 0),
            business_metrics.get("total_members", 1),
        )
        * 100
    )

    visits_per_active_member = safe_divide(
        business_metrics.get("total_visits", 0),
        business_metrics.get("active_members", 1),
    )

    revenue_per_visit = safe_divide(
        business_metrics.get("total_revenue", 0),
        business_metrics.get("total_visits", 1),
    )

    store_revenue_share = (
        safe_divide(
            business_metrics.get("store_revenue", 0),
            business_metrics.get("total_revenue", 1),
        )
        * 100
    )

    # Quality assessments
    retention_quality = (
        "Excellent"
        if business_metrics.get("member_retention_rate", 0) > 75
        else "Monitor"
    )
    session_quality = (
        "Quality" if business_metrics.get("avg_visit_duration", 0) > 1.5 else "Monitor"
    )

    # Activation status
    activation_status = "🟢" if member_activation_rate > 70 else "🟡"
    retention_status = (
        "🟢" if business_metrics.get("member_retention_rate", 0) > 75 else "🟡"
    )
    session_status = (
        "🟢" if business_metrics.get("avg_visit_duration", 0) > 1.5 else "🟡"
    )

    # Store performance assessment
    store_performance = (
        "🟢 Good store revenue contribution"
        if store_revenue_share > 20
        else "🟡 Consider boosting store sales"
    )

    # Renewal insights
    repurchase_rate = repurchase_analytics.get("repurchase_rate", 0)
    if repurchase_rate > 60:
        renewal_insight = (
            f"🟢 Your retention rate of {repurchase_rate:.1f}% is excellent!"
        )
    elif repurchase_rate > 40:
        renewal_insight = f"🟡 Your retention rate of {repurchase_rate:.1f}% is good, but there's room for improvement."
    else:
        renewal_insight = f"🔴 Your retention rate of {repurchase_rate:.1f}% needs attention. Consider member engagement programs."

    return {
        "member_activation_rate": member_activation_rate,
        "member_activation_percentage": f"{member_activation_rate:.0f}% of Total",
        "visits_per_active_member": visits_per_active_member,
        "revenue_per_visit": revenue_per_visit,
        "store_revenue_share": store_revenue_share,
        "retention_quality": retention_quality,
        "session_quality": session_quality,
        "activation_status": activation_status,
        "retention_status": retention_status,
        "session_status": session_status,
        "store_performance": store_performance,
        "renewal_insight": renewal_insight,
    }


def business_analytics_view(request):
    """Comprehensive business intelligence dashboard"""
    if not request.user.is_staff:
        raise PermissionDenied

    # Get date range from request - simplified like weekly_metrics_view
    analysis_type = request.GET.get("type", "overview")

    today = timezone.now().date()
    end_date_str = request.GET.get("end_date", today.strftime("%Y-%m-%d"))
    start_date_str = request.GET.get(
        "start_date", (today - timedelta(days=7)).strftime("%Y-%m-%d")
    )

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Convert to datetime with timezone for consistency with rest of the code
        start_date = datetime.combine(start_date, datetime.min.time()).replace(
            tzinfo=timezone.get_current_timezone()
        )
        end_date = datetime.combine(end_date, datetime.min.time()).replace(
            tzinfo=timezone.get_current_timezone()
        )
    except ValueError:
        # Handle invalid date format - use default dates
        start_date = timezone.now() - timedelta(days=7)
        end_date = timezone.now()

    # Calculate comprehensive business metrics
    business_metrics = calculate_business_metrics(start_date, end_date)
    revenue_analytics = calculate_revenue_analytics(start_date, end_date)
    sales_analytics = calculate_sales_analytics(start_date, end_date)
    visit_analytics = calculate_visit_analytics(start_date, end_date)
    member_analytics = calculate_member_analytics(start_date, end_date)
    repurchase_analytics = calculate_repurchase_analytics(start_date, end_date)

    # Calculate additional KPI metrics for enhanced dashboard
    enhanced_kpis = calculate_enhanced_kpis(business_metrics, repurchase_analytics)

    context = {
        **admin_site.each_context(request),
        "title": "Business Intelligence Dashboard",
        "business_metrics": business_metrics,
        "enhanced_kpis": enhanced_kpis,
        "revenue_analytics": json.dumps(revenue_analytics, cls=DecimalEncoder),
        "sales_analytics": json.dumps(sales_analytics, cls=DecimalEncoder),
        "visit_analytics": json.dumps(visit_analytics, cls=DecimalEncoder),
        "member_analytics": json.dumps(member_analytics, cls=DecimalEncoder),
        "repurchase_analytics": repurchase_analytics,
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

    # IMPROVED Logic to get repurchase data
    # Step 1: Find members whose membership expires in the selected week
    expiring_members = Member.objects.filter(
        active_until__date__gte=start_date, active_until__date__lte=end_date
    ).distinct()

    # Step 1.5: Filter to only include members who have EVER purchased actual membership packages (non-"-0")
    # This excludes members who only ever bought single-visit passes
    actual_expiring_members = (
        expiring_members.filter(payment__package__code__isnull=False)
        .exclude(payment__package__code__endswith="-0")
        .distinct()
    )

    # Step 2: Get ALL membership payments made during the week (regardless of member expiry status)
    # BUT only for existing members who had previous payments (exclude new member first-time purchases)
    all_weekly_membership_payments = (
        Payment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
            package__code__isnull=False,
        )
        .exclude(package__code__endswith="-0")
        .select_related("member", "package")
        .order_by("payment_date")
    )

    # Filter to only include members who had PREVIOUS payments before this week
    # (This excludes new members making their first purchase)
    existing_member_ids = set(
        Payment.objects.filter(
            payment_date__date__lt=start_date,  # Before this week
            package__code__isnull=False,
        )
        .exclude(package__code__endswith="-0")
        .values_list("member_id", flat=True)
        .distinct()
    )

    # Separate installment payments from renewals
    installment_payments = all_weekly_membership_payments.filter(
        member_id__in=existing_member_ids
    ).filter(Q(apakah_nyicil=True) | Q(notes__icontains="CICILAN"))

    # Only analyze non-installment payments by existing members for renewals
    renewal_payments = all_weekly_membership_payments.filter(
        member_id__in=existing_member_ids
    ).exclude(Q(apakah_nyicil=True) | Q(notes__icontains="CICILAN"))

    # Step 3: Categorize payments into expiring renewals vs early renewals
    expiring_renewals_info = []
    early_renewals_info = []
    installment_payments_info = []
    expiring_renewed_member_ids = set()

    for payment in renewal_payments:
        member = payment.member

        # Calculate what the member's original expiry date was BEFORE this payment
        original_expiry_date = None
        package_duration_months = payment.get_duration_from_package()

        if package_duration_months is not None and payment.membership_end_date:
            # Work backwards: original_expiry = new_expiry - package_duration
            from dateutil.relativedelta import relativedelta

            original_expiry_date = payment.membership_end_date - relativedelta(
                months=package_duration_months
            )
            original_expiry_date = original_expiry_date.date()

        # Determine if this member's original membership was expiring during target week
        if original_expiry_date and start_date <= original_expiry_date <= end_date:
            # This is an expiring member renewal (membership was going to expire this week)
            expiring_renewals_info.append(
                {
                    "member": member,
                    "payment_date": payment.payment_date,
                    "amount": payment.amount,
                    "package_code": payment.package.code if payment.package else "N/A",
                    "notes": payment.notes,
                    "renewal_type": "expiring",
                    "original_expiry": original_expiry_date,
                }
            )
            expiring_renewed_member_ids.add(member.id)
        else:
            # This is an early renewal (membership was not expiring this week)
            early_renewals_info.append(
                {
                    "member": member,
                    "payment_date": payment.payment_date,
                    "amount": payment.amount,
                    "package_code": payment.package.code if payment.package else "N/A",
                    "notes": payment.notes,
                    "renewal_type": "early",
                    "current_expiry": (
                        member.active_until.date()
                        if member.active_until
                        else "No expiry set"
                    ),
                    "original_expiry": original_expiry_date,
                }
            )

    # Step 3.5: Process installment payments
    for payment in installment_payments:
        installment_payments_info.append(
            {
                "member": payment.member,
                "payment_date": payment.payment_date,
                "amount": payment.amount,
                "package_code": payment.package.code if payment.package else "N/A",
                "notes": payment.notes,
                "payment_type": "installment",
            }
        )

    # Step 4: Members who didn't repurchase (expired but no renewal)
    did_not_repurchase_members = actual_expiring_members.exclude(
        id__in=expiring_renewed_member_ids
    )

    # Step 5: Calculate statistics
    total_expiring = actual_expiring_members.count()
    total_expiring_renewed = len(expiring_renewed_member_ids)
    total_early_renewals = len(early_renewals_info)
    total_installment_payments = len(installment_payments_info)
    total_all_renewals = total_expiring_renewed + total_early_renewals

    # Ensure we don't have more renewals than expiring members (logic consistency)
    # If we have renewals for members who weren't in our original expiring list,
    # we should count them as expiring for the rate calculation
    effective_total_expiring = max(total_expiring, total_expiring_renewed)

    expiring_repurchase_rate = (
        (total_expiring_renewed / effective_total_expiring) * 100
        if effective_total_expiring > 0
        else 0
    )

    # Combine all renewals for backward compatibility
    repurchased_members_info = expiring_renewals_info + early_renewals_info
    total_repurchased = total_all_renewals
    repurchase_rate = (
        expiring_repurchase_rate  # Keep original meaning: expiring renewal rate
    )

    # Additional weekly queries
    # 1. All payments for the week with member details (equivalent to first SQL query)
    weekly_payments = (
        Payment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
        )
        .select_related("member", "package")
        .order_by("id")
    )

    # 2. Total revenue for the week
    total_weekly_revenue = (
        Payment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # 3. Total visits for the week
    total_weekly_visits = Visit.objects.filter(
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date,
    ).count()

    # 4. Total tamu (guests) for the week
    total_weekly_tamu = Tamu.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).count()

    # 5. Detailed tamu list for the week
    weekly_tamu_details = Tamu.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).order_by("created_at")

    # 6. New Members logic - members who did their first membership package payment (not *-0) within the date range
    new_members_payments = []
    
    # Get all payments for membership packages (not *-0) within the date range
    membership_payments_in_week = Payment.objects.filter(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
        package__code__isnull=False,
    ).exclude(
        package__code__endswith="-0"  # Excludes: 0-BRONZE-0, REG0
    ).exclude(
        package__code__contains="VISIT"  # Excludes: KELASAVISIT, KELASBVISIT
    ).exclude(
        package__code__startswith="PT"  # Excludes all PT packages
    ).select_related("member", "package").order_by("payment_date")

    # Pre-fetch all previous membership payments to avoid N+1 queries
    # Get all member IDs who had any membership payments before the start of this week
    members_with_prior_payments = set(
        Payment.objects.filter(
            payment_date__date__lt=start_date,
            package__code__isnull=False,
        )
        .exclude(package__code__endswith="-0")
        .exclude(package__code__contains="VISIT")
        .exclude(package__code__startswith="PT")
        .values_list("member_id", flat=True)
        .distinct()
    )
    
    # For each payment, check if this is the member's first membership package payment
    # Since membership_payments_in_week is ordered by payment_date ASC, the first encounter per member IS their earliest payment
    seen_new_member_ids = set()
    for payment in membership_payments_in_week:
        member = payment.member
        
        # If no prior membership payments and we haven't seen this member yet, this is a new member
        if payment.member_id not in members_with_prior_payments and payment.member_id not in seen_new_member_ids:
            seen_new_member_ids.add(payment.member_id)
            new_members_payments.append({
                "member": member,
                "payment_date": payment.payment_date,
                "payment_amount": payment.amount,
                "package_code": payment.package.code if payment.package else "N/A",
                "payment_note": payment.notes or "",
                "is_pemula": member.is_pemula,
                "address": member.address,
                "goals": member.goals,
                "know_mulai_gym_from": member.know_mulai_gym_from,
                "why_choose_mulai": member.why_choose_mulai,
            })

    # Member tracking flags counts (irrespective of date)
    total_asked_referral = Member.objects.filter(asked_referral=True).count()
    total_asked_google_review = Member.objects.filter(asked_google_review=True).count()
    total_missed_installment = Member.objects.filter(missed_installment=True).count()

    # Additional all-time metrics
    total_equipment_views = Equipment.objects.aggregate(total=Sum("total_views"))["total"] or 0
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_active_members = Member.objects.filter(active_until__gte=today_start).count()

    context = {
        **admin_site.each_context(request),
        "title": "Weekly Metrics Tracker",
        "start_date": start_date,
        "end_date": end_date,
        "repurchase_rate": repurchase_rate,
        "expiring_repurchase_rate": expiring_repurchase_rate,
        "total_expiring": total_expiring,
        "total_repurchased": total_repurchased,
        "total_expiring_renewed": total_expiring_renewed,
        "total_early_renewals": total_early_renewals,
        "total_installment_payments": total_installment_payments,
        "total_all_renewals": total_all_renewals,
        # Individual renewal lists
        "repurchased_members": repurchased_members_info,  # All renewals combined (backward compatibility)
        "expiring_renewals": expiring_renewals_info,
        "early_renewals": early_renewals_info,
        "installment_payments": installment_payments_info,
        "did_not_repurchase_members": did_not_repurchase_members,
        # Weekly overview metrics
        "weekly_payments": weekly_payments,
        "total_weekly_revenue": total_weekly_revenue,
        "total_weekly_visits": total_weekly_visits,
        "total_weekly_tamu": total_weekly_tamu,
        "weekly_tamu_details": weekly_tamu_details,
        "new_members_payments": new_members_payments,
        # Member tracking flags (all-time counts)
        "total_asked_referral": total_asked_referral,
        "total_asked_google_review": total_asked_google_review,
        "total_missed_installment": total_missed_installment,
        "total_equipment_views": total_equipment_views,
        "total_active_members": total_active_members,
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

    # Daily sales trend (using local timezone GMT+7)
    daily_sales = (
        Sale.objects.filter(created_at__gte=start_date)
        .extra(select={"day": "date(created_at + INTERVAL '7 hours')"})
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

    # Daily visit patterns (using local timezone GMT+7)
    daily_visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(select={"day": "date(check_in_time + INTERVAL '7 hours')"})
        .values("day")
        .annotate(
            total_visits=Count("id"), unique_members=Count("member", distinct=True)
        )
        .order_by("day")
    )

    # Hourly patterns - filter by business hours 07:00-21:00 Jakarta time
    hourly_data = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(
            select={"hour": "extract(hour from (check_in_time + INTERVAL '7 hours'))"},
            where=[
                "extract(hour from (check_in_time + INTERVAL '7 hours')) BETWEEN %s AND %s"
            ],
            params=[7, 21],
        )
        .values("hour")
        .annotate(total_visits=Count("id"))
        .order_by("hour")
    )

    # Create complete business hours dataset (07:00-21:00)
    hourly_dict = {int(item["hour"]): item["total_visits"] for item in hourly_data}
    hourly_visits = []
    for hour in range(7, 22):  # 07:00 to 21:00 (inclusive)
        hourly_visits.append({"hour": hour, "total_visits": hourly_dict.get(hour, 0)})

    # Member visit frequency
    member_frequencies = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .values("member")
        .annotate(visit_count=Count("id"))
        .values("visit_count")
        .annotate(member_count=Count("member"))
        .order_by("visit_count")
    )

    # Average session duration (using local timezone GMT+7)
    avg_duration_by_day = (
        Visit.objects.filter(
            check_in_time__gte=start_date, check_out_time__isnull=False
        )
        .extra(select={"day": "date(check_in_time + INTERVAL '7 hours')"})
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

    # Enhanced Visit Insights

    # 1. Weekly patterns - which days are busiest
    weekly_patterns = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(
            select={"weekday": "extract(dow from (check_in_time + INTERVAL '7 hours'))"}
        )
        .values("weekday")
        .annotate(
            total_visits=Count("id"), unique_members=Count("member", distinct=True)
        )
        .order_by("weekday")
    )

    # Convert to readable day names
    day_names = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]
    weekly_visits = []
    weekday_dict = {int(item["weekday"]): item for item in weekly_patterns}

    for day_num in range(7):
        day_data = weekday_dict.get(day_num, {"total_visits": 0, "unique_members": 0})
        weekly_visits.append(
            {
                "day_name": day_names[day_num],
                "day_short": day_names[day_num][:3],
                "weekday": day_num,
                "total_visits": day_data["total_visits"],
                "unique_members": day_data["unique_members"],
            }
        )

    # 2. Session Duration Analysis (by 15-minute buckets)
    session_duration_buckets = [
        {"label": "<30m", "min_minutes": 0, "max_minutes": 30, "count": 0},
        {"label": "30-45m", "min_minutes": 30, "max_minutes": 45, "count": 0},
        {"label": "45-60m", "min_minutes": 45, "max_minutes": 60, "count": 0},
        {"label": "60-75m", "min_minutes": 60, "max_minutes": 75, "count": 0},
        {"label": "75-90m", "min_minutes": 75, "max_minutes": 90, "count": 0},
        {"label": "90-105m", "min_minutes": 90, "max_minutes": 105, "count": 0},
        {"label": "105-120m", "min_minutes": 105, "max_minutes": 120, "count": 0},
        {"label": "120-135m", "min_minutes": 120, "max_minutes": 135, "count": 0},
        {"label": "135-150m", "min_minutes": 135, "max_minutes": 150, "count": 0},
        {"label": "150-165m", "min_minutes": 150, "max_minutes": 165, "count": 0},
        {"label": "165-180m", "min_minutes": 165, "max_minutes": 180, "count": 0},
        {"label": ">3h", "min_minutes": 180, "max_minutes": None, "count": 0},
    ]

    # Get all completed sessions with duration (use EXTRACT to convert interval to minutes)
    completed_visits = (
        Visit.objects.filter(
            check_in_time__gte=start_date, check_out_time__isnull=False
        )
        .extra(
            select={
                "duration_minutes": "EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 60"
            }
        )
        .values("duration_minutes")
    )

    # Categorize sessions into buckets
    for visit in completed_visits:
        duration = int(visit["duration_minutes"]) if visit["duration_minutes"] else 0
        for bucket in session_duration_buckets:
            if bucket["max_minutes"] is None:  # Last bucket (>2.5h)
                if duration >= bucket["min_minutes"]:
                    bucket["count"] += 1
                    break
            else:
                if bucket["min_minutes"] <= duration < bucket["max_minutes"]:
                    bucket["count"] += 1
                    break

    # 3. Member visit frequency distribution (clear breakdown)
    member_visit_patterns = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .values("member")
        .annotate(visit_count=Count("id"))
    )

    # Create frequency distribution: how many members visited X times
    visit_frequency_distribution = {}
    for member_data in member_visit_patterns:
        visits = member_data["visit_count"]
        if visits in visit_frequency_distribution:
            visit_frequency_distribution[visits] += 1
        else:
            visit_frequency_distribution[visits] = 1

    # Convert to sorted list for chart display
    frequency_chart_data = []
    for visit_count in sorted(visit_frequency_distribution.keys()):
        member_count = visit_frequency_distribution[visit_count]
        frequency_chart_data.append(
            {
                "visit_count": visit_count,
                "member_count": member_count,
                "label": f"{visit_count} visit{'s' if visit_count > 1 else ''}",
            }
        )

    # 4. Basic session stats
    total_visits = Visit.objects.filter(check_in_time__gte=start_date).count()
    completed_sessions = Visit.objects.filter(
        check_in_time__gte=start_date, check_out_time__isnull=False
    ).count()
    checkout_rate = (completed_sessions / max(total_visits, 1)) * 100

    return {
        "daily_visits": daily_visits_list,
        "hourly_patterns": hourly_visits,
        "member_frequencies": list(member_frequencies),
        "session_durations": session_durations_list,
        # Enhanced insights
        "weekly_patterns": weekly_visits,
        "session_duration_buckets": session_duration_buckets,
        "visit_frequency_distribution": frequency_chart_data,
        "basic_stats": {
            "total_visits": total_visits,
            "completed_sessions": completed_sessions,
            "checkout_rate": round(checkout_rate, 1),
        },
    }


def calculate_member_analytics(start_date, end_date):
    """Calculate member acquisition and retention analytics"""

    # Member acquisition trend (using local timezone GMT+7)
    monthly_signups = (
        Member.objects.filter(created_at__gte=start_date)
        .extra(select={"month": "date_trunc('month', created_at + INTERVAL '7 hours')"})
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
# Temporary file with the new view functions to append to visits/admin.py


def visits_by_duration_view(request):
    """AJAX endpoint for visits by duration bucket"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    duration_bucket = request.GET.get("bucket")
    if not duration_bucket:
        return JsonResponse({"error": "Duration bucket required"}, status=400)

    # Get date range (same logic as other views)
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()
    end_date = now
    if period_type == "7_days":
        start_date = now - timedelta(days=7)
    elif period_type == "2_weeks":
        start_date = now - timedelta(weeks=2)
    elif period_type == "4_weeks":
        start_date = now - timedelta(weeks=4)
    else:
        start_date = now - timedelta(days=7)

    # Parse duration bucket to get min/max minutes
    bucket_mapping = {
        "<30m": (0, 30),
        "30-45m": (30, 45),
        "45-60m": (45, 60),
        "60-75m": (60, 75),
        "75-90m": (75, 90),
        "90-105m": (90, 105),
        "105-120m": (105, 120),
        "120-135m": (120, 135),
        "135-150m": (135, 150),
        "150-165m": (150, 165),
        "165-180m": (165, 180),
        ">3h": (180, None),
    }

    if duration_bucket not in bucket_mapping:
        return JsonResponse({"error": "Invalid duration bucket"}, status=400)

    min_minutes, max_minutes = bucket_mapping[duration_bucket]

    # Build query based on duration range
    visits_query = Visit.objects.filter(
        check_in_time__gte=start_date, check_out_time__isnull=False
    ).extra(
        select={
            "duration_minutes": "EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 60"
        }
    )

    # Filter by duration bucket
    if max_minutes is None:  # ">3h" case
        visits = visits_query.extra(
            where=["EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 60 >= %s"],
            params=[min_minutes],
        )
    else:
        visits = visits_query.extra(
            where=[
                "EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 60 >= %s AND EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 60 < %s"
            ],
            params=[min_minutes, max_minutes],
        )

    # Get visit details
    visit_list = []
    for visit in visits.select_related("member")[:100]:  # Limit to 100 results
        duration_seconds = (visit.check_out_time - visit.check_in_time).total_seconds()
        duration_minutes = int(duration_seconds / 60)

        visit_list.append(
            {
                "id": visit.id,
                "member_name": visit.member.name if visit.member else "Unknown",
                "member_email": visit.member.email if visit.member else "",
                "check_in": visit.check_in_time.strftime("%Y-%m-%d %H:%M"),
                "check_out": visit.check_out_time.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": duration_minutes,
                "duration_display": (
                    f"{duration_minutes//60}h {duration_minutes%60}m"
                    if duration_minutes >= 60
                    else f"{duration_minutes}m"
                ),
            }
        )

    return JsonResponse(
        {"bucket": duration_bucket, "count": len(visit_list), "visits": visit_list}
    )


def visits_by_frequency_view(request):
    """AJAX endpoint for members by visit frequency"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    visit_count = request.GET.get("visit_count")
    if not visit_count:
        return JsonResponse({"error": "Visit count required"}, status=400)

    try:
        visit_count = int(visit_count)
    except ValueError:
        return JsonResponse({"error": "Invalid visit count"}, status=400)

    # Get date range
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()
    end_date = now
    if period_type == "7_days":
        start_date = now - timedelta(days=7)
    elif period_type == "2_weeks":
        start_date = now - timedelta(weeks=2)
    elif period_type == "4_weeks":
        start_date = now - timedelta(weeks=4)
    else:
        start_date = now - timedelta(days=7)

    # Get members with exact visit count
    members_with_visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .values("member")
        .annotate(total_visits=Count("id"))
        .filter(total_visits=visit_count)
    )

    member_list = []
    for member_data in members_with_visits:
        member = Member.objects.get(id=member_data["member"])

        # Get recent visits for this member
        recent_visits = Visit.objects.filter(
            member=member, check_in_time__gte=start_date
        ).order_by("-check_in_time")[:5]

        visit_details = []
        for visit in recent_visits:
            visit_details.append(
                {
                    "check_in": visit.check_in_time.strftime("%Y-%m-%d %H:%M"),
                    "check_out": (
                        visit.check_out_time.strftime("%Y-%m-%d %H:%M")
                        if visit.check_out_time
                        else "Not checked out"
                    ),
                }
            )

        member_list.append(
            {
                "id": member.id,
                "name": member.name,
                "email": member.email,
                "phone": member.phone_number,
                "visit_count": member_data["total_visits"],
                "recent_visits": visit_details,
            }
        )

    return JsonResponse(
        {
            "visit_count": visit_count,
            "member_count": len(member_list),
            "members": member_list,
        }
    )


def visits_by_day_view(request):
    """AJAX endpoint for visits by day of week"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    day = request.GET.get("day")
    if day is None:
        return JsonResponse({"error": "Day required"}, status=400)

    try:
        day_num = int(day)
    except ValueError:
        return JsonResponse({"error": "Invalid day"}, status=400)

    # Get date range
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()
    end_date = now
    if period_type == "7_days":
        start_date = now - timedelta(days=7)
    elif period_type == "2_weeks":
        start_date = now - timedelta(weeks=2)
    elif period_type == "4_weeks":
        start_date = now - timedelta(weeks=4)
    else:
        start_date = now - timedelta(days=7)

    # Get visits for specific day of week
    visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(
            where=["extract(dow from (check_in_time + INTERVAL '7 hours')) = %s"],
            params=[day_num],
        )
        .select_related("member")
        .order_by("-check_in_time")[:100]
    )

    visit_list = []
    for visit in visits:
        visit_list.append(
            {
                "id": visit.id,
                "member_name": visit.member.name if visit.member else "Unknown",
                "check_in": visit.check_in_time.strftime("%Y-%m-%d %H:%M"),
                "check_out": (
                    visit.check_out_time.strftime("%Y-%m-%d %H:%M")
                    if visit.check_out_time
                    else "Not checked out"
                ),
                "day_name": [
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                ][day_num],
            }
        )

    return JsonResponse(
        {
            "day": day_num,
            "day_name": [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ][day_num],
            "count": len(visit_list),
            "visits": visit_list,
        }
    )


def visits_by_hour_view(request):
    """AJAX endpoint for visits by hour"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

    hour = request.GET.get("hour")
    if hour is None:
        return JsonResponse({"error": "Hour required"}, status=400)

    try:
        hour_num = int(hour)
    except ValueError:
        return JsonResponse({"error": "Invalid hour"}, status=400)

    # Get date range
    period_type = request.GET.get("period_type", "7_days")
    now = timezone.now()
    end_date = now
    if period_type == "7_days":
        start_date = now - timedelta(days=7)
    elif period_type == "2_weeks":
        start_date = now - timedelta(weeks=2)
    elif period_type == "4_weeks":
        start_date = now - timedelta(weeks=4)
    else:
        start_date = now - timedelta(days=7)

    # Get visits for specific hour
    visits = (
        Visit.objects.filter(check_in_time__gte=start_date)
        .extra(
            where=["extract(hour from (check_in_time + INTERVAL '7 hours')) = %s"],
            params=[hour_num],
        )
        .select_related("member")
        .order_by("-check_in_time")[:100]
    )

    visit_list = []
    for visit in visits:
        visit_list.append(
            {
                "id": visit.id,
                "member_name": visit.member.name if visit.member else "Unknown",
                "check_in": visit.check_in_time.strftime("%Y-%m-%d %H:%M"),
                "check_out": (
                    visit.check_out_time.strftime("%Y-%m-%d %H:%M")
                    if visit.check_out_time
                    else "Not checked out"
                ),
            }
        )

    return JsonResponse(
        {
            "hour": hour_num,
            "hour_display": f"{hour_num:02d}:00",
            "count": len(visit_list),
            "visits": visit_list,
        }
    )
    
