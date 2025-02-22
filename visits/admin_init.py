from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
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
        list_display = ('name', 'email', 'phone_number', 'is_active_member')
        search_fields = ('name', 'email', 'phone_number')
        list_filter = ('is_active_member', 'gender')
    admin_site.register(Member, MemberAdmin)

if not admin_site._registry.get(Payment):
    class PaymentAdmin(admin.ModelAdmin):
        list_display = ('member', 'formatted_amount', 'duration_days', 'payment_date', 'membership_end_date')
        search_fields = ('member__name', 'member__email')
        list_filter = ('payment_date',)

        def formatted_amount(self, obj):
            return f"Rp {obj.amount:,.0f}"
        formatted_amount.short_description = 'Amount'
    admin_site.register(Payment, PaymentAdmin)

# Visit model is already registered in visits/admin.py 