from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponse
from django.shortcuts import render
import csv

from visits.admin import admin_site
from .models import Member, ActiveMember, User, Tamu, Masukkan, Prospect
from payments.models import Payment
from purchases.models import Sale, SaleItem
from visits.models import Visit
from classes.models import ClassInstance


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "user_type")
    list_filter = ("user_type",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "user_type",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )


class WhatsAppLinkMixin:
    def whatsapp_link(self, obj):
        phone = obj.phone_number
        if not phone:
            return "-"

        # Clean the phone number for the URL
        cleaned_phone = "".join(filter(str.isdigit, phone))
        if cleaned_phone.startswith("0"):
            cleaned_phone = "62" + cleaned_phone[1:]

        # url = f"https://wa.me/{cleaned_phone}"
        # return format_html('<a href="{}" target="_blank">{}</a>', url, phone)
        return cleaned_phone

    whatsapp_link.short_description = "No. HP (WhatsApp)"
    whatsapp_link.admin_order_field = "phone_number"


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = (
        "package",
        "amount",
        "formatted_amount",
        "payment_date",
        "membership_end_date",
        "payment_method",
        "apakah_nyicil",
        "notes",
        "created_by",
    )
    fields = (
        "payment_date",
        "package",
        "formatted_amount",
        "payment_method",
        "apakah_nyicil",
        "membership_end_date",
        "notes",
        "created_by",
    )
    ordering = ["-payment_date"]

    def formatted_amount(self, obj):
        if obj.amount:
            return f"Rp {obj.amount:,.0f}"
        return "-"

    formatted_amount.short_description = "Amount"

    def get_total_payments(self, member):
        """Calculate total payments for the member"""
        from django.db.models import Sum

        total = (
            Payment.objects.filter(member=member).aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
        return f"Total Payments: Rp {total:,.0f}"

    get_total_payments.short_description = "Total Payments"

    def has_add_permission(self, request, obj=None):
        return False  # Prevent adding payments from member detail page


class SaleInline(admin.TabularInline):
    model = Sale
    extra = 0
    can_delete = False
    readonly_fields = (
        "created_at",
        "total_amount",
        "formatted_total_amount",
        "items_list",
        "payment_method",
        "notes",
        "created_by",
    )
    fields = (
        "created_at",
        "items_list",
        "formatted_total_amount",
        "payment_method",
        "notes",
        "created_by",
    )
    ordering = ["-created_at"]

    def formatted_total_amount(self, obj):
        if obj.total_amount:
            return f"Rp {obj.total_amount:,.0f}"
        return "-"

    formatted_total_amount.short_description = "Total Amount"

    def items_list(self, obj):
        """Show detailed list of items purchased in this sale"""
        items = obj.items.all()
        if not items:
            return "No items"

        item_details = []
        for item in items:
            unit_price = (
                f"Rp {item.price_at_purchase:,.0f}"
                if item.price_at_purchase
                else "Rp 0"
            )
            total_price = (
                f"Rp {item.price_at_purchase * item.quantity:,.0f}"
                if item.price_at_purchase
                else "Rp 0"
            )
            item_details.append(
                f"{item.quantity}x {item.product.name} @ {unit_price} = {total_price}"
            )

        return format_html("<br/>".join(item_details))

    items_list.short_description = "Items Purchased"

    def get_total_sales(self, member):
        """Calculate total sales for the member"""
        from django.db.models import Sum

        total = (
            Sale.objects.filter(member=member).aggregate(total=Sum("total_amount"))[
                "total"
            ]
            or 0
        )
        return f"Total Sales: Rp {total:,.0f}"

    get_total_sales.short_description = "Total Sales"

    def has_add_permission(self, request, obj=None):
        return False  # Prevent adding sales from member detail page


class MemberAdmin(WhatsAppLinkMixin, admin.ModelAdmin):
    inlines = [PaymentInline, SaleInline]
    list_display = (
        "name",
        "email",
        "whatsapp_link",
        "is_pemula",
        "formatted_active_until",
        "formatted_pemula_active_until",
        "formatted_semi_private_active_until",
        "pt_session_count",
        "asked_referral",
        "asked_google_review",
        "missed_installment",
        "skip_auto_reminder",
        "membership_status",
        "created_at",
    )
    list_filter = (
        "gender",
        "is_pemula",
        "asked_referral",
        "asked_google_review",
        "missed_installment",
        "skip_auto_reminder",
        "created_at",
    )
    list_editable = ("asked_referral", "asked_google_review", "missed_installment", "skip_auto_reminder")
    search_fields = ("name", "email", "phone_number")
    change_list_template = "admin/accounts/member/change_list.html"
    readonly_fields = (
        "created_at",
        "total_payments",
        "total_sales",
        "visit_history_panel",
        "class_booking_history_panel",
    )
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "email",
                    "phone_number",
                    "gender",
                    "social_media_username",
                )
            },
        ),
        (
            "Physical Information",
            {"fields": ("age", "height", "weight", "years_of_working_out")},
        ),
        (
            "Membership Information",
            {
                "fields": (
                    "active_until",
                    "pemula_active_until",
                    "semi_private_active_until",
                    "pt_session_count",
                    "is_pemula",
                )
            },
        ),
        (
            "Admin Tracking Flags",
            {
                "fields": (
                    "asked_referral",
                    "asked_google_review",
                    "missed_installment",
                    "skip_auto_reminder",
                )
            },
        ),
        (
            "Transaction Summary",
            {
                "fields": (
                    "total_payments",
                    "total_sales",
                )
            },
        ),
        (
            "Additional Information",
            {"fields": ("address", "goals", "know_mulai_gym_from", "why_choose_mulai")},
        ),
        (
            "Visit History",
            {"fields": ("visit_history_panel",)},
        ),
        (
            "Class Booking History",
            {"fields": ("class_booking_history_panel",)},
        ),
        (
            "Admin Note",
            {
                "fields": ("notes",),
                "description": "Catatan internal admin saja, tidak ditampilkan ke member.",
            },
        ),
    )

    def formatted_active_until(self, obj):
        if obj.active_until:
            return timezone.localtime(obj.active_until).strftime("%d %b %Y")
        return "-"

    formatted_active_until.short_description = "Active Until"

    def formatted_pemula_active_until(self, obj):
        if obj.pemula_active_until:
            return timezone.localtime(obj.pemula_active_until).strftime("%d %b %Y")
        return "-"

    formatted_pemula_active_until.short_description = "Pemula Active Until"

    def formatted_semi_private_active_until(self, obj):
        if obj.semi_private_active_until:
            return timezone.localtime(obj.semi_private_active_until).strftime(
                "%d %b %Y"
            )
        return "-"

    formatted_semi_private_active_until.short_description = "Semi Private Active Until"

    def membership_status(self, obj):
        if obj.is_active_member:
            return "Active"
        return "Expired"

    membership_status.short_description = "Status"

    def total_payments(self, obj):
        """Calculate total payments for this member"""
        from django.db.models import Sum

        total = (
            Payment.objects.filter(member=obj).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        return f"Rp {total:,.0f}"

    total_payments.short_description = "Total Payments"

    def total_sales(self, obj):
        """Calculate total sales for this member"""
        from django.db.models import Sum

        total = (
            Sale.objects.filter(member=obj).aggregate(total=Sum("total_amount"))[
                "total"
            ]
            or 0
        )
        return f"Rp {total:,.0f}"

    total_sales.short_description = "Total Sales"

    def visit_history_panel(self, obj):
        """Render recent visit history with a summary at the top (limited list)."""
        if not obj:
            return "-"

        # Totals
        total_visits = Visit.objects.filter(member=obj).count()

        # Average duration across visits that have a checkout
        visits_with_duration = Visit.objects.filter(
            member=obj, check_out_time__isnull=False
        )
        if visits_with_duration.exists():
            total_seconds = sum(
                [
                    (v.check_out_time - v.check_in_time).total_seconds()
                    for v in visits_with_duration
                ]
            )
            avg_seconds = int(total_seconds / visits_with_duration.count())
            avg_hours = avg_seconds // 3600
            avg_minutes = (avg_seconds % 3600) // 60
            avg_str = (
                f"{avg_hours}h {avg_minutes}m" if avg_hours > 0 else f"{avg_minutes}m"
            )
        else:
            avg_str = "N/A"

        # Recent visits (pagination-lite)
        recent_visits = Visit.objects.filter(member=obj).order_by("-check_in_time")[:20]

        rows = []
        rows.append(
            f'<div style="margin-bottom:6px;">'
            f'<strong style="color:#28a745;">🏋️ TOTAL: {total_visits} visits (Avg: {avg_str})</strong>'
            f"</div>"
        )

        if not recent_visits:
            rows.append("No visits found.")
        else:
            for v in recent_visits:
                check_in = (
                    timezone.localtime(v.check_in_time).strftime("%d %b %Y %H:%M")
                    if v.check_in_time
                    else "-"
                )
                if v.check_out_time:
                    check_out = timezone.localtime(v.check_out_time).strftime(
                        "%d %b %Y %H:%M"
                    )
                    duration_td = (
                        v.check_out_time - v.check_in_time if v.check_in_time else None
                    )
                    if duration_td:
                        total_min = int(duration_td.total_seconds() // 60)
                        hours = total_min // 60
                        minutes = total_min % 60
                        duration_str = (
                            f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                        )
                    else:
                        duration_str = "-"
                else:
                    check_out = "Still in gym"
                    duration_str = "-"

                rows.append(
                    f"<div>"
                    f"<strong>Check-in:</strong> {check_in} &nbsp; | &nbsp; "
                    f"<strong>Check-out:</strong> {check_out} &nbsp; | &nbsp; "
                    f"<strong>Duration:</strong> {duration_str}"
                    f"</div>"
                )

        return format_html("".join(rows))

    visit_history_panel.short_description = "Visit History (Recent 20)"

    def class_booking_history_panel(self, obj):
        """Render class booking history with a summary at the top (limited list)."""
        if not obj:
            return "-"

        # Booked and waitlisted classes
        booked_qs = (
            ClassInstance.objects.filter(booked_members=obj)
            .select_related("class_schedule__class_obj")
            .order_by("-date", "-start_time")[:10]
        )
        waitlisted_qs = (
            ClassInstance.objects.filter(waitlisted_members=obj)
            .select_related("class_schedule__class_obj")
            .order_by("-date", "-start_time")[:5]
        )

        total_booked = ClassInstance.objects.filter(booked_members=obj).count()
        total_waitlisted = ClassInstance.objects.filter(waitlisted_members=obj).count()

        rows = []
        rows.append(
            f'<div style="margin-bottom:6px;">'
            f'<strong style="color:#0066cc;">📚 TOTAL: {total_booked} booked, {total_waitlisted} waitlisted</strong>'
            f"</div>"
        )

        if booked_qs:
            rows.append("<div><strong>Recent Booked Classes:</strong></div>")
            for ci in booked_qs:
                status_color = "green" if ci.status == "COMPLETED" else "orange"
                rows.append(
                    f'<div style="color:{status_color}">'
                    f"✓ {ci.class_schedule.class_obj.name} - "
                    f"{ci.date.strftime('%d %b %Y')} {ci.start_time.strftime('%H:%M')} "
                    f"({ci.status})"
                    f"</div>"
                )

        if waitlisted_qs:
            rows.append(
                '<div style="margin-top:6px;"><strong>Current Waitlist:</strong></div>'
            )
            for ci in waitlisted_qs:
                rows.append(
                    f'<div style="color:gray">'
                    f"⏳ {ci.class_schedule.class_obj.name} - "
                    f"{ci.date.strftime('%d %b %Y')} {ci.start_time.strftime('%H:%M')} "
                    f"(WAITLISTED)"
                    f"</div>"
                )

        if len(rows) == 1:  # Only summary added, no details
            rows.append("No class bookings found.")

        return format_html("".join(rows))

    class_booking_history_panel.short_description = (
        "Class Booking History (Recent 10 + Waitlist)"
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_members_csv),
                name="accounts_member_export_csv",
            ),
        ]
        return custom_urls + urls

    def export_members_csv(self, request):
        """Export all members as CSV (SELECT * FROM accounts_member ORDER BY id DESC)"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="members_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        # Header row - all fields
        writer.writerow(
            [
                "id",
                "name",
                "email",
                "phone_number",
                "gender",
                "age",
                "height",
                "weight",
                "address",
                "social_media_username",
                "years_of_working_out",
                "goals",
                "know_mulai_gym_from",
                "why_choose_mulai",
                "active_until",
                "pemula_active_until",
                "semi_private_active_until",
                "pt_session_count",
                "is_pemula",
                "asked_referral",
                "asked_google_review",
                "missed_installment",
                "skip_auto_reminder",
                "created_at",
            ]
        )

        members = Member.objects.all().order_by("-id")
        for m in members:
            writer.writerow(
                [
                    m.id,
                    m.name,
                    m.email,
                    m.phone_number,
                    m.gender,
                    m.age,
                    m.height,
                    m.weight,
                    m.address,
                    m.social_media_username,
                    m.years_of_working_out,
                    m.goals,
                    m.know_mulai_gym_from,
                    m.why_choose_mulai,
                    (
                        timezone.localtime(m.active_until).strftime("%Y-%m-%d %H:%M:%S")
                        if m.active_until
                        else ""
                    ),
                    (
                        timezone.localtime(m.pemula_active_until).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if m.pemula_active_until
                        else ""
                    ),
                    (
                        timezone.localtime(m.semi_private_active_until).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if m.semi_private_active_until
                        else ""
                    ),
                    m.pt_session_count,
                    m.is_pemula,
                    m.asked_referral,
                    m.asked_google_review,
                    m.missed_installment,
                    m.skip_auto_reminder,
                    timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response


class ActiveMemberAdmin(MemberAdmin):
    """Admin for viewing only active members with all the same features as MemberAdmin"""

    change_list_template = "admin/accounts/activemember/change_list.html"

    def has_module_permission(self, request):
        """Use Member's permissions instead of ActiveMember's"""
        return request.user.has_perm("accounts.view_member")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("accounts.view_member")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("accounts.change_member")

    def has_add_permission(self, request):
        # Disable add - users should add via Member admin
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("accounts.delete_member")

    def get_queryset(self, request):
        """Filter to only show active members"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return super().get_queryset(request).filter(active_until__gte=today_start)

    def get_urls(self):
        """Override to use different URL names for active member exports"""
        urls = admin.ModelAdmin.get_urls(self)
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_active_members_csv),
                name="accounts_activemember_export_csv",
            ),
        ]
        return custom_urls + urls

    def export_active_members_csv(self, request):
        """Export active members only as CSV"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="active_members_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "name",
                "email",
                "phone_number",
                "gender",
                "age",
                "height",
                "weight",
                "address",
                "social_media_username",
                "years_of_working_out",
                "goals",
                "know_mulai_gym_from",
                "why_choose_mulai",
                "active_until",
                "pemula_active_until",
                "semi_private_active_until",
                "pt_session_count",
                "is_pemula",
                "asked_referral",
                "asked_google_review",
                "missed_installment",
                "skip_auto_reminder",
                "created_at",
            ]
        )

        for m in self.get_queryset(request).order_by("-id"):
            writer.writerow(
                [
                    m.id,
                    m.name,
                    m.email,
                    m.phone_number,
                    m.gender,
                    m.age,
                    m.height,
                    m.weight,
                    m.address,
                    m.social_media_username,
                    m.years_of_working_out,
                    m.goals,
                    m.know_mulai_gym_from,
                    m.why_choose_mulai,
                    (
                        timezone.localtime(m.active_until).strftime("%Y-%m-%d %H:%M:%S")
                        if m.active_until
                        else ""
                    ),
                    (
                        timezone.localtime(m.pemula_active_until).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if m.pemula_active_until
                        else ""
                    ),
                    (
                        timezone.localtime(m.semi_private_active_until).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if m.semi_private_active_until
                        else ""
                    ),
                    m.pt_session_count,
                    m.is_pemula,
                    m.asked_referral,
                    m.asked_google_review,
                    m.missed_installment,
                    m.skip_auto_reminder,
                    timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response


class TamuAdmin(WhatsAppLinkMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "whatsapp_link",
        "is_pemula",
        "has_worked_out_before",
        "social_media_username",
        "created_at",
    )
    list_filter = ("is_pemula", "has_worked_out_before", "created_at")
    search_fields = ("name", "phone_number", "social_media_username")
    readonly_fields = ("created_at",)


class MasukkanAdmin(admin.ModelAdmin):
    list_display = ("get_display_name", "contact", "feedback_snippet", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "contact", "feedback")
    readonly_fields = ("created_at",)
    list_display_links = ("get_display_name",)

    def get_display_name(self, obj):
        return obj.name or f"Feedback #{obj.id}"

    get_display_name.short_description = "Name"
    get_display_name.admin_order_field = "name"

    def feedback_snippet(self, obj):
        return obj.feedback[:50] + "..." if len(obj.feedback) > 50 else obj.feedback

    feedback_snippet.short_description = "Feedback"


class ProspectAdmin(WhatsAppLinkMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "whatsapp_link",
        "social_media_username",
        "created_by",
        "created_at",
    )
    search_fields = (
        "name",
        "phone_number",
        "social_media_username",
        "notes",
        "created_by__username",
    )
    list_filter = ("created_by", "created_at")
    readonly_fields = ("created_at", "created_by")

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Set created_by only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


admin_site.register(User, CustomUserAdmin)
admin_site.register(Member, MemberAdmin)
admin_site.register(ActiveMember, ActiveMemberAdmin)
admin_site.register(Tamu, TamuAdmin)
admin_site.register(Masukkan, MasukkanAdmin)
admin_site.register(Prospect, ProspectAdmin)
