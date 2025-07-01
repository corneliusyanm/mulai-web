from django.contrib import admin
from django.db.models import Sum, F

from .models import Product, Sale, SaleItem


class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active", "description")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_editable = ("price", "is_active")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1  # Start with one empty slot for a product
    autocomplete_fields = ["product"]
    readonly_fields = ("price_at_purchase",)
    fields = ("product", "quantity", "price_at_purchase")


class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = (
        "id",
        "created_at",
        "created_by",
        "member",
        "payment_method",
        "formatted_total_amount",
        "notes",
    )
    list_filter = ("created_at", "member", "payment_method")
    search_fields = ("member__name", "member__email", "id")
    autocomplete_fields = ["member"]
    readonly_fields = ("total_amount", "created_at", "created_by")

    fieldsets = (
        (None, {"fields": ("member", "payment_method", "notes")}),
        ("Sale Info", {"fields": ("total_amount", "created_at", "created_by")}),
    )

    def formatted_total_amount(self, obj):
        return f"Rp {obj.total_amount:,.0f}"

    formatted_total_amount.short_description = "Total Amount"

    def save_model(self, request, obj, form, change):
        # Set the creator to the current user
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # After saving all the inline items, update the total for the sale
        form.instance.update_total_amount()
