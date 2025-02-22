from django.contrib import admin
from django.utils import timezone
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('member', 'formatted_amount', 'duration_days', 'formatted_payment_date', 
                   'formatted_membership_end', 'membership_status')
    list_filter = ('payment_date',)
    search_fields = ('member__email', 'member__name', 'member__phone_number')
    readonly_fields = ('membership_end_date',)
    fields = ('member', 'amount', 'duration_days', 'payment_date', 
             'membership_end_date', 'notes')

    def formatted_amount(self, obj):
        return f"Rp {obj.amount:,.0f}"
    formatted_amount.short_description = 'Amount'

    def formatted_payment_date(self, obj):
        return timezone.localtime(obj.payment_date).strftime("%d %b %Y %H:%M")
    formatted_payment_date.short_description = 'Payment Date'

    def formatted_membership_end(self, obj):
        return timezone.localtime(obj.membership_end_date).strftime("%d %b %Y %H:%M")
    formatted_membership_end.short_description = 'Membership End Date'

    def membership_status(self, obj):
        if obj.membership_end_date > timezone.now():
            return 'Active'
        return 'Expired'
    membership_status.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new payments
            obj.created_by = request.user
        obj.member.is_active_member = True
        obj.member.active_until = obj.membership_end_date
        obj.member.save()
        super().save_model(request, obj, form, change)
