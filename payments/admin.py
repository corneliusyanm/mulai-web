from django.contrib import admin
from django.utils import timezone
from django import forms
from .models import Payment

class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ('member', 'amount', 'duration_choice', 'duration_days', 'payment_date', 'notes')
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'duration_choice': forms.RadioSelect(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide duration_days field initially (will be shown via JavaScript if Custom is selected)
        if 'duration_days' in self.fields:
            self.fields['duration_days'].widget.attrs['style'] = 'display: none;'
            self.fields['duration_days'].widget.attrs['class'] = 'custom-duration-field'
        
    def clean(self):
        cleaned_data = super().clean()
        duration_choice = cleaned_data.get('duration_choice')
        duration_days = cleaned_data.get('duration_days')
        
        # If custom duration is selected, duration_days is required
        if duration_choice == 0 and not duration_days:
            self.add_error('duration_days', 'Please enter custom duration days')
            
        return cleaned_data

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentAdminForm
    list_display = ('member', 'formatted_amount', 'get_duration_display', 'formatted_payment_date', 
                   'formatted_membership_end', 'membership_status')
    list_filter = ('payment_date',)
    search_fields = ('member__email', 'member__name', 'member__phone_number')
    fields = ('member', 'amount', 'duration_choice', 'duration_days', 'payment_date', 'notes')
    
    def get_duration_display(self, obj):
        if obj.duration_choice == 0:
            return f"{obj.duration_days} days (Custom)"
        return dict(Payment.DURATION_CHOICES).get(obj.duration_choice)
    get_duration_display.short_description = 'Duration'

    def formatted_amount(self, obj):
        return f"Rp {obj.amount:,.0f}"
    formatted_amount.short_description = 'Amount'

    def formatted_payment_date(self, obj):
        return timezone.localtime(obj.payment_date).strftime("%d %b %Y")
    formatted_payment_date.short_description = 'Payment Date'

    def formatted_membership_end(self, obj):
        return timezone.localtime(obj.membership_end_date).strftime("%d %b %Y")
    formatted_membership_end.short_description = 'Membership End Date'

    def membership_status(self, obj):
        if obj.membership_end_date > timezone.now():
            return 'Active'
        return 'Expired'
    membership_status.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new payments
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        
    class Media:
        js = ('js/payment_admin.js',)
