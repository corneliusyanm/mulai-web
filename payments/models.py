from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Member


class Package(models.Model):
    code = models.CharField(max_length=20, unique=True)
    default_price = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.code} - Rp {self.default_price:,.0f} ({self.description})"

    class Meta:
        ordering = ["code"]


class Payment(models.Model):
    DURATION_CHOICES = [
        (1, "1 Day"),
        (30, "1 Month"),
        (90, "3 Months"),
        (180, "6 Months"),
        (365, "12 Months"),
        (0, "Custom"),  # For custom duration input
    ]

    PAYMENT_METHOD_CHOICES = [
        ("TRANSFER", "Transfer"),
        ("QRIS", "QRIS"),
        ("CASH", "Cash"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=0)  # Changed for Rupiah
    payment_date = models.DateTimeField(default=timezone.now)
    duration_choice = models.IntegerField(choices=DURATION_CHOICES, default=30)
    duration_days = models.IntegerField(
        help_text="Custom duration in days", null=True, blank=True
    )
    membership_end_date = models.DateTimeField(
        editable=False
    )  # Make it not editable in forms
    notes = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default="TRANSFER",
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payments",
    )
    apakah_nyicil = models.BooleanField(default=False, help_text="Apakah cicilan?")
    skip_membership_update = models.BooleanField(
        default=False,
        help_text="Skip automatic membership update (manual update required)",
    )

    def parse_package_code(self):
        """Parse package code to determine membership type and duration"""
        if not self.package or not self.package.code:
            return None, None, None

        parts = self.package.code.split("-")
        if len(parts) < 3:
            return None, None, None

        type_num = parts[0]
        level = parts[1]

        # Handle ADD packages which have format: 5-ADD-SILVER-1 or 5-ADD-GOLD-3
        if type_num == "5" and level == "ADD" and len(parts) >= 4:
            addon_type = parts[2]  # SILVER, GOLD, DIAMOND
            duration = parts[3]  # 1, 3, 6, 12, etc.
            return type_num, f"{level}-{addon_type}", duration
        else:
            # Regular packages: 0-BRONZE-1, 1-SILVER-3, etc.
            duration = parts[2]
            return type_num, level, duration

    def get_duration_from_package(self):
        """Get duration in months based on package code"""
        _, _, duration_str = self.parse_package_code()
        if duration_str is None:
            return None

        try:
            duration_num = int(duration_str)
            if duration_num == 0:
                return 0  # Special case: 1 day (0 months)
            else:
                return duration_num  # months
        except ValueError:
            return None

    def calculate_end_date(self, current_date, duration_months):
        """Calculate end date based on current active date and duration"""
        today = timezone.now().date()
        start_date = None

        # Determine start date based on current membership status
        if current_date and current_date.date() >= today:
            # Member is active, start new period after current one ends
            start_date = current_date.date() + timedelta(days=1)
        else:
            # Member is inactive or has no active date, start from payment date
            start_date = self.payment_date.date() if self.payment_date else today

        # Calculate end date
        end_time = datetime.max.time()  # End of day

        if duration_months == 0:  # 1 day only
            end_date = start_date
        else:
            end_date = (
                start_date + relativedelta(months=duration_months) - timedelta(days=1)
            )

        return timezone.make_aware(datetime.combine(end_date, end_time))

    def update_member_memberships(self):
        """Update member's membership fields based on package type"""
        if self.skip_membership_update:
            return

        type_num, level, duration_str = self.parse_package_code()
        if not type_num:
            # Fallback to old duration_choice logic if no package
            self.update_legacy_membership()
            return

        duration_months = self.get_duration_from_package()
        if duration_months is None:
            return

        member_fields_to_update = []

        # Determine which fields to update based on package type
        if type_num == "0":  # BRONZE - only active_until
            new_date = self.calculate_end_date(
                self.member.active_until, duration_months
            )
            self.member.active_until = new_date
            self.membership_end_date = new_date
            member_fields_to_update.append("active_until")

        elif type_num == "1":  # SILVER - active_until + pemula_active_until
            new_active_date = self.calculate_end_date(
                self.member.active_until, duration_months
            )
            new_pemula_date = self.calculate_end_date(
                self.member.pemula_active_until, duration_months
            )

            self.member.active_until = new_active_date
            self.member.pemula_active_until = new_pemula_date
            self.membership_end_date = new_active_date
            member_fields_to_update.extend(["active_until", "pemula_active_until"])

        elif type_num == "2":  # GOLD - active_until + semi_private_active_until
            new_active_date = self.calculate_end_date(
                self.member.active_until, duration_months
            )
            new_semi_private_date = self.calculate_end_date(
                self.member.semi_private_active_until, duration_months
            )

            self.member.active_until = new_active_date
            self.member.semi_private_active_until = new_semi_private_date
            self.membership_end_date = new_active_date
            member_fields_to_update.extend(
                ["active_until", "semi_private_active_until"]
            )

        elif type_num == "3":  # PLATINUM - active_until + pemula + semi_private
            new_active_date = self.calculate_end_date(
                self.member.active_until, duration_months
            )
            new_pemula_date = self.calculate_end_date(
                self.member.pemula_active_until, duration_months
            )
            new_semi_private_date = self.calculate_end_date(
                self.member.semi_private_active_until, duration_months
            )

            self.member.active_until = new_active_date
            self.member.pemula_active_until = new_pemula_date
            self.member.semi_private_active_until = new_semi_private_date
            self.membership_end_date = new_active_date
            member_fields_to_update.extend(
                ["active_until", "pemula_active_until", "semi_private_active_until"]
            )

        elif (
            type_num == "4"
        ):  # DIAMOND - only active_until (ignore PT sessions for now)
            new_date = self.calculate_end_date(
                self.member.active_until, duration_months
            )
            self.member.active_until = new_date
            self.membership_end_date = new_date
            member_fields_to_update.append("active_until")

        elif type_num == "5":  # ADD-ON packages
            if level.startswith("ADD-"):
                addon_type = level.split("-")[1]  # SILVER, GOLD, DIAMOND
                if addon_type == "SILVER":
                    new_pemula_date = self.calculate_end_date(
                        self.member.pemula_active_until, duration_months
                    )
                    self.member.pemula_active_until = new_pemula_date
                    self.membership_end_date = new_pemula_date
                    member_fields_to_update.append("pemula_active_until")
                elif addon_type == "GOLD":
                    new_semi_private_date = self.calculate_end_date(
                        self.member.semi_private_active_until, duration_months
                    )
                    self.member.semi_private_active_until = new_semi_private_date
                    self.membership_end_date = new_semi_private_date
                    member_fields_to_update.append("semi_private_active_until")
                # ADD-DIAMOND does nothing per requirements

        # Save member with updated fields
        if member_fields_to_update:
            self.member.save(update_fields=member_fields_to_update)

    def update_legacy_membership(self):
        """Fallback to old logic when no package is specified"""
        today = timezone.now().date()
        start_date = None

        # Determine start date based on member's current status
        if self.member.active_until and self.member.active_until.date() >= today:
            # Member is active, start new period after current one ends
            start_date = self.member.active_until.date() + timedelta(days=1)
        else:
            # Member is inactive or has no active_until, start from payment date
            start_date = self.payment_date.date() if self.payment_date else today

        # Calculate end date based on duration choice and start_date
        end_date = start_date
        end_time = datetime.max.time()  # Default to end of day

        if self.duration_choice == 1:  # 1 Day
            end_date = start_date
        elif self.duration_choice == 30:  # 1 Month
            end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        elif self.duration_choice == 90:  # 3 Months
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        elif self.duration_choice == 180:  # 6 Months
            end_date = start_date + relativedelta(months=6) - timedelta(days=1)
        elif self.duration_choice == 365:  # 12 Months
            end_date = start_date + relativedelta(months=12) - timedelta(days=1)
        elif self.duration_choice == 0 and self.duration_days:  # Custom
            end_date = start_date + timedelta(days=self.duration_days - 1)
        else:
            end_date = start_date

        # Set the membership end date
        self.membership_end_date = timezone.make_aware(
            datetime.combine(end_date, end_time)
        )

        # Update member's active_until
        self.member.active_until = self.membership_end_date
        self.member.save(update_fields=["active_until"])

    def save(self, *args, **kwargs):
        # Only calculate membership end date for new payments or if explicitly needed
        calculate_end_date = not self.pk or not self.membership_end_date

        if calculate_end_date:
            # Set a default membership_end_date initially
            if not self.membership_end_date:
                self.membership_end_date = timezone.now()

        # Call the original save method first to ensure the payment has an ID if new
        super().save(*args, **kwargs)

        # Update member memberships based on package type
        if self.member and calculate_end_date:
            self.update_member_memberships()
            # Save again to update the membership_end_date if it was calculated
            if self.membership_end_date != timezone.now():
                super().save(update_fields=["membership_end_date"])

    def __str__(self):
        return f"{self.member.name} - Rp {self.amount:,.0f} - {self.payment_date.strftime('%d %b %Y')}"

    class Meta:
        ordering = ["-payment_date"]
