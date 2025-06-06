from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from accounts.models import Member, User
from payments.models import Payment, Package
from visits.admin import VisitAdmin, admin_site
from visits.models import Visit
from payments.admin import PaymentAdminForm

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
            "member",
            "get_package_code",
            "formatted_amount",
            "get_duration_display",
            "formatted_payment_date",
            "formatted_membership_end",
            "membership_status",
            "payment_method",
            "created_by",
        )
        list_filter = ("payment_date", "payment_method", "package")
        search_fields = ("member__email", "member__name", "member__phone_number")

        fieldsets = (
            (
                None,
                {
                    "fields": (
                        "member",
                        "package",
                        "amount",
                        "duration_choice",
                        "duration_days",
                        "payment_date",
                        "payment_method",
                        "notes",
                    ),
                },
            ),
        )

        def get_package_code(self, obj):
            if obj.package:
                return obj.package.code
            return "-"

        get_package_code.short_description = "Package"

        def get_duration_display(self, obj):
            if obj.duration_choice == 0:
                return f"{obj.duration_days} days (Custom)"
            return dict(Payment.DURATION_CHOICES).get(obj.duration_choice)

        get_duration_display.short_description = "Duration"

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

        def save_model(self, request, obj, form, change):
            # Always set created_by to current user
            obj.created_by = request.user
            super().save_model(request, obj, form, change)

        class Media:
            js = ("js/payment_admin.js",)

    admin_site.register(Payment, CustomPaymentAdmin)

# Visit model is already registered in visits/admin.py

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
