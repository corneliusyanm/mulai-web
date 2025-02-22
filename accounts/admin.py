from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Member

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type')
    list_filter = ('user_type',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('name', 'email', 'phone_number')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone_number', 'gender')
        }),
        ('Physical Information', {
            'fields': ('age', 'height', 'weight', 'years_of_working_out')
        }),
        ('Additional Information', {
            'fields': ('goals', 'know_mulai_gym_from')
        }),
    )

admin.site.register(User, CustomUserAdmin)
