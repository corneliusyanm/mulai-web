from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html

from visits.admin import admin_site
from .models import Member, User, Tamu, Masukkan, Prospect
from payments.models import Payment
from purchases.models import Sale, SaleItem


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
        "membership_status",
        "created_at",
    )
    list_filter = ("gender", "is_pemula", "created_at")
    search_fields = ("name", "email", "phone_number")
    readonly_fields = ("created_at", "total_payments", "total_sales")
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
admin_site.register(Tamu, TamuAdmin)
admin_site.register(Masukkan, MasukkanAdmin)
admin_site.register(Prospect, ProspectAdmin)
