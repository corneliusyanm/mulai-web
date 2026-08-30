from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponse
import csv

from accounts.models import Member, User
from payments.models import Payment, Package
from visits.admin import VisitAdmin, admin_site
from visits.models import Visit
from reminders.models import Reminder
from reminders.admin import ReminderAdmin
from classes.models import (
    BookingPenalty,
    Class,
    ClassInstance,
    ClassMiss,
    GymClosure,
    PenaltySettings,
)
from classes.admin import (
    BookingPenaltyAdmin,
    ClassAdmin,
    ClassInstanceAdmin,
    ClassMissAdmin,
    GymClosureAdmin,
    PenaltySettingsAdmin,
)
from payments.admin import PaymentAdminForm

# Import the new models and admin configurations from the purchases app
from purchases.models import Product, Sale, SaleItem
from purchases.admin import ProductAdmin, SaleAdmin

# Only register if not already registered
if not admin_site._registry.get(User):

    class CustomUserAdmin(UserAdmin):
        list_display = ("username", "email", "user_type", "is_active")
        list_filter = ("user_type", "is_active")
        fieldsets = UserAdmin.fieldsets + (
            ("Additional Info", {"fields": ("user_type", "phone_number")}),
        )

    admin_site.register(User, CustomUserAdmin)

if not admin_site._registry.get(Member):

    class MemberAdmin(admin.ModelAdmin):
        list_display = (
            "name",
            "email",
            "phone_number",
            "formatted_active_until",
            "membership_status",
        )
        search_fields = ("name", "email", "phone_number")
        list_filter = ("gender",)

        def formatted_active_until(self, obj):
            if obj.active_until:
                return timezone.localtime(obj.active_until).strftime("%d %b %Y")
            return "-"

        formatted_active_until.short_description = "Active Until"

        def membership_status(self, obj):
            # Consider active if end date is today or in the future
            if obj.is_active_member:
                return "Active"
            return "Expired"

        membership_status.short_description = "Status"

    admin_site.register(Member, MemberAdmin)

if not admin_site._registry.get(Payment):

    class CustomPaymentAdmin(admin.ModelAdmin):
        form = PaymentAdminForm
        list_display = (
            "clickable_id",
            "clickable_member",
            "get_package_display",
            "formatted_amount",
            "formatted_payment_date",
            "formatted_membership_end",
            "membership_status",
            "payment_method",
            "get_membership_types_updated",
            "get_created_by_display",
        )
        list_filter = ("payment_date", "payment_method", "package")
        search_fields = ("member__email", "member__name", "member__phone_number")
        autocomplete_fields = ["member"]
        change_list_template = "admin/payments/payment/change_list.html"

        fieldsets = (
            (
                None,
                {
                    "fields": (
                        "member",
                        "package",
                        "amount",
                        "payment_date",
                        "payment_method",
                        "apakah_nyicil",
                        "skip_membership_update",
                        "notes",
                    ),
                },
            ),
        )

        def get_urls(self):
            urls = super().get_urls()
            custom_urls = [
                path(
                    "export-csv/",
                    self.admin_site.admin_view(self.export_payments_csv),
                    name="payments_payment_export_csv",
                ),
            ]
            return custom_urls + urls

        def export_payments_csv(self, request):
            """Export payments with member details as CSV"""
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="payments_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            )

            writer = csv.writer(response)
            writer.writerow(
                [
                    "payment_id",
                    "amount",
                    "member_id",
                    "name",
                    "payment_date",
                    "notes",
                    "package_code",
                    "apakah_nyicil",
                    "gender",
                    "age",
                    "is_pemula",
                    "know_mulai_gym_from",
                    "why_choose_mulai",
                    "goals",
                ]
            )

            # Query matching the SQL: exclude ids 16, 17, 46
            payments = (
                Payment.objects.select_related("member", "package")
                .exclude(id__in=[16, 17, 46])
                .order_by("-id")
            )

            for p in payments:
                writer.writerow(
                    [
                        p.id,
                        p.amount,
                        p.member.id if p.member else "",
                        p.member.name if p.member else "",
                        (
                            timezone.localtime(p.payment_date).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            if p.payment_date
                            else ""
                        ),
                        p.notes or "",
                        p.package.code if p.package else "",
                        p.apakah_nyicil,
                        p.member.gender if p.member else "",
                        p.member.age if p.member else "",
                        p.member.is_pemula if p.member else "",
                        p.member.know_mulai_gym_from if p.member else "",
                        p.member.why_choose_mulai if p.member else "",
                        p.member.goals if p.member else "",
                    ]
                )

            return response

        def clickable_id(self, obj):
            """Clickable ID that links to the payment detail page"""
            url = reverse("admin:payments_payment_change", args=[obj.id])
            return format_html('<a href="{}">{}</a>', url, obj.id)

        clickable_id.short_description = "ID"
        clickable_id.admin_order_field = "id"

        def clickable_member(self, obj):
            """Clickable member name that links to the member detail page"""
            url = reverse("admin:accounts_member_change", args=[obj.member.id])
            return format_html('<a href="{}">{}</a>', url, obj.member.name)

        clickable_member.short_description = "Member"
        clickable_member.admin_order_field = "member__name"

        def get_package_display(self, obj):
            if obj.package:
                return f"{obj.package.code} - {obj.package.description}"
            return "No Package"

        get_package_display.short_description = "Package"

        def get_membership_types_updated(self, obj):
            if obj.skip_membership_update:
                return "Skipped"

            if not obj.package:
                return "Legacy"

            type_num, level, _ = obj.parse_package_code()

            if type_num == "0":  # BRONZE
                return "Gym"
            elif type_num == "1":  # SILVER
                return "Gym + Pemula"
            elif type_num == "2":  # GOLD
                return "Gym + Semi Private"
            elif type_num == "3":  # PLATINUM
                return "Gym + All Classes"
            elif type_num == "4":  # DIAMOND
                return "Gym + PT"
            elif type_num == "5":  # ADD-ON
                if "SILVER" in level:
                    return "Pemula Only"
                elif "GOLD" in level:
                    return "Semi Private Only"
                elif "DIAMOND" in level:
                    return "PT Only"

            return "Unknown"

        get_membership_types_updated.short_description = "Membership Type"

        def formatted_amount(self, obj):
            return f"Rp {obj.amount:,.0f}"

        formatted_amount.short_description = "Amount"

        def formatted_payment_date(self, obj):
            return timezone.localtime(obj.payment_date).strftime("%d %b %Y")

        formatted_payment_date.short_description = "Payment Date"

        def formatted_membership_end(self, obj):
            return timezone.localtime(obj.membership_end_date).strftime("%d %b %Y")

        formatted_membership_end.short_description = "Membership End Date"

        def membership_status(self, obj):
            today_start = timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if obj.membership_end_date >= today_start:
                return "Active"
            return "Expired"

        membership_status.short_description = "Status"

        def get_created_by_display(self, obj):
            if obj.created_by:
                return obj.created_by.username
            return "Unknown"

        get_created_by_display.short_description = "Created By"

        def save_model(self, request, obj, form, change):
            # Set created_by to current user only on creation (not on updates)
            if not change:  # This means it's a new object being created
                obj.created_by = request.user
            super().save_model(request, obj, form, change)

        class Media:
            js = ("js/payment_admin.js",)

    admin_site.register(Payment, CustomPaymentAdmin)

# Register models from the purchases app
if not admin_site._registry.get(Product):
    admin_site.register(Product, ProductAdmin)

if not admin_site._registry.get(Sale):

    class CustomSaleAdmin(SaleAdmin):
        change_list_template = "admin/purchases/sale/change_list.html"

        def get_urls(self):
            urls = super().get_urls()
            custom_urls = [
                path(
                    "export-csv/",
                    self.admin_site.admin_view(self.export_sales_csv),
                    name="purchases_sale_export_csv",
                ),
            ]
            return custom_urls + urls

        def export_sales_csv(self, request):
            """Export sales with product details as CSV"""
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="sales_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            )

            writer = csv.writer(response)
            writer.writerow(
                [
                    "sale_id",
                    "created_at",
                    "total_amount",
                    "notes",
                    "member_name",
                    "payment_method",
                    "product_name",
                    "quantity",
                    "price_at_purchase",
                ]
            )

            # Query matching the SQL: exclude DITRAKTIR_ONEL payment method
            sales = (
                Sale.objects.select_related("member")
                .exclude(payment_method="DITRAKTIR_ONEL")
                .order_by("-created_at", "-id")
            )

            for sale in sales:
                sale_items = SaleItem.objects.filter(sale=sale).select_related(
                    "product"
                )

                if sale_items.exists():
                    for item in sale_items:
                        writer.writerow(
                            [
                                sale.id,
                                (
                                    timezone.localtime(sale.created_at).strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                    if sale.created_at
                                    else ""
                                ),
                                sale.total_amount,
                                sale.notes or "",
                                sale.member.name if sale.member else "",
                                sale.payment_method or "",
                                item.product.name if item.product else "",
                                item.quantity,
                                item.price_at_purchase,
                            ]
                        )
                else:
                    # Sale with no items
                    writer.writerow(
                        [
                            sale.id,
                            (
                                timezone.localtime(sale.created_at).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                if sale.created_at
                                else ""
                            ),
                            sale.total_amount,
                            sale.notes or "",
                            sale.member.name if sale.member else "",
                            sale.payment_method or "",
                            "",
                            "",
                            "",
                        ]
                    )

            return response

    admin_site.register(Sale, CustomSaleAdmin)

# Register Visit model to custom admin site
if not admin_site._registry.get(Visit):
    admin_site.register(Visit, VisitAdmin)

# Register Package model
if not admin_site._registry.get(Package):  # Check if Package is already registered

    class PackageAdmin(admin.ModelAdmin):
        list_display = ("code", "default_price", "description")
        search_fields = ("code", "description")
        list_editable = (
            "default_price",
            "description",
        )  # Optional: Allow editing these directly in the list view
        ordering = ("code",)

    admin_site.register(Package, PackageAdmin)

# Register Reminder model
if not admin_site._registry.get(Reminder):
    admin_site.register(Reminder, ReminderAdmin)

# Register Class models
if not admin_site._registry.get(Class):
    admin_site.register(Class, ClassAdmin)

if not admin_site._registry.get(ClassInstance):
    admin_site.register(ClassInstance, ClassInstanceAdmin)

# No-show penalty: the rules, the misses, and the penalties handed out
if not admin_site._registry.get(GymClosure):
    admin_site.register(GymClosure, GymClosureAdmin)

if not admin_site._registry.get(PenaltySettings):
    admin_site.register(PenaltySettings, PenaltySettingsAdmin)

if not admin_site._registry.get(ClassMiss):
    admin_site.register(ClassMiss, ClassMissAdmin)

if not admin_site._registry.get(BookingPenalty):
    admin_site.register(BookingPenalty, BookingPenaltyAdmin)
