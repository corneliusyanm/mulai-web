from django.conf import settings
from django.db import models
from django.db.models import Sum, F

from accounts.models import Member


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True, help_text="Uncheck this to hide the product from new sales."
    )

    def __str__(self):
        return f"{self.name} - Rp {self.price:,.0f}"

    class Meta:
        ordering = ["name"]


class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("QRIS", "QRIS"),
        ("TRANSFER", "Transfer"),
        ("DITRAKTIR_ONEL", "Ditraktir Onel"),
    ]
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_sales",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional: Link this sale to a gym member.",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, editable=False
    )
    notes = models.TextField(blank=True)

    def update_total_amount(self):
        """Calculates the total amount from all its SaleItem entries."""
        total = (
            self.items.aggregate(
                total=Sum(
                    F("quantity") * F("price_at_purchase"),
                    output_field=models.DecimalField(),
                )
            )["total"]
            or 0
        )
        self.total_amount = total
        self.save(update_fields=["total_amount"])

    def __str__(self):
        return f"Sale on {self.created_at.strftime('%Y-%m-%d %H:%M')} for Rp {self.total_amount:,.0f}"

    class Meta:
        ordering = ["-created_at"]


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(
        max_digits=10, decimal_places=0, editable=False
    )

    def save(self, *args, **kwargs):
        if not self.price_at_purchase:
            self.price_at_purchase = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
