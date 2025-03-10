from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from accounts.models import User, Member
from payments.models import Payment
from visits.models import Visit
from visits.admin import admin_site, VisitAdmin

# Only register if not already registered
if not admin_site._registry.get(User):
    class CustomUserAdmin(UserAdmin):
        list_display = ('username', 'email', 'user_type', 'is_active')
        list_filter = ('user_type', 'is_active')
        fieldsets = UserAdmin.fieldsets + (
            ('Additional Info', {'fields': ('user_type', 'phone_number')}),
        )
    admin_site.register(User, CustomUserAdmin)

if not admin_site._registry.get(Member):
    class MemberAdmin(admin.ModelAdmin):
        list_display = ('name', 'email', 'phone_number', 'formatted_active_until', 'membership_status')
        search_fields = ('name', 'email', 'phone_number')
        list_filter = ('gender',)
        
        def formatted_active_until(self, obj):
            if obj.active_until:
                return timezone.localtime(obj.active_until).strftime("%d %b %Y")
            return "-"
        formatted_active_until.short_description = 'Active Until'
        
        def membership_status(self, obj):
            if obj.is_active_member:
                return 'Active'
            return 'Expired'
        membership_status.short_description = 'Status'
        
    admin_site.register(Member, MemberAdmin)

if not admin_site._registry.get(Payment):
    class PaymentAdmin(admin.ModelAdmin):
        list_display = ('member', 'formatted_amount', 'get_duration_display', 'formatted_payment_date', 
                       'formatted_membership_end')
        search_fields = ('member__name', 'member__email')
        list_filter = ('payment_date',)

        def formatted_amount(self, obj):
            return f"Rp {obj.amount:,.0f}"
        formatted_amount.short_description = 'Amount'
        
        def get_duration_display(self, obj):
            if hasattr(obj, 'duration_choice') and obj.duration_choice == 0:
                return f"{obj.duration_days} days (Custom)"
            elif hasattr(obj, 'duration_choice'):
                return dict(Payment.DURATION_CHOICES).get(obj.duration_choice)
            return f"{obj.duration_days} days"
        get_duration_display.short_description = 'Duration'
        
        def formatted_payment_date(self, obj):
            return timezone.localtime(obj.payment_date).strftime("%d %b %Y")
        formatted_payment_date.short_description = 'Payment Date'
        
        def formatted_membership_end(self, obj):
            return timezone.localtime(obj.membership_end_date).strftime("%d %b %Y")
        formatted_membership_end.short_description = 'Membership End Date'
        
    admin_site.register(Payment, PaymentAdmin)

# Visit model is already registered in visits/admin.py 