from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone

from .models import Visit


class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)

        # Add Quick Access section only on the main admin page
        if app_label is None:
            visit_app = next(
                (app for app in app_list if app['app_label'] == 'visits'), None)
            if visit_app:
                visit_app['models'].extend([
                    {
                        'name': 'Currently Visiting',
                        'object_name': 'Currently Visiting',
                        'admin_url': reverse('admin:current-visits'),
                        'view_only': True,
                        'perms': {'view': True}
                    },
                    {
                        'name': 'Visit History',
                        'object_name': 'Visit History',
                        'admin_url': reverse('admin:visit-history'),
                        'view_only': True,
                        'perms': {'view': True}
                    }
                ])

        return app_list


# Create an instance of the custom admin site
admin_site = CustomAdminSite(name='custom_admin')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'formatted_check_in',
        'formatted_check_out',
        'visit_status')
    list_filter = (
        ('check_in_time', DateFieldListFilter),
        ('check_out_time', DateFieldListFilter),
    )
    search_fields = ('member__name', 'member__email', 'member__phone_number')
    change_list_template = 'admin/visits/visit/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'current/',
                self.current_visits_view,
                name='current-visits'),
            path(
                'history/',
                self.visit_history_view,
                name='visit-history'),
            path(
                'checkout/<int:visit_id>/',
                self.checkout_visit,
                name='checkout-visit'),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        # Show most recent visits first
        return super().get_queryset(request).order_by('-check_in_time')

    def formatted_check_in(self, obj):
        return timezone.localtime(obj.check_in_time).strftime("%d %b %Y %H:%M")
    formatted_check_in.short_description = 'Check In Time'

    def formatted_check_out(self, obj):
        if obj.check_out_time:
            return timezone.localtime(
                obj.check_out_time).strftime("%d %b %Y %H:%M")
        return '-'
    formatted_check_out.short_description = 'Check Out Time'

    def visit_status(self, obj):
        if not obj.check_out_time:
            return 'Currently Visiting'
        return 'Completed'
    visit_status.short_description = 'Status'

    def checkout_visit(self, request, visit_id):
        try:
            visit = Visit.objects.get(id=visit_id)
            if not visit.check_out_time:
                visit.check_out_time = timezone.now()
                visit.save()
                messages.success(
                    request, f'Successfully checked out {visit.member.name}')
            else:
                messages.warning(request, 'Visit already checked out')
        except Visit.DoesNotExist:
            messages.error(request, 'Visit not found')
        return redirect('admin:current-visits')

    def current_visits_view(self, request):
        visits = Visit.objects.filter(
            check_out_time__isnull=True
        ).order_by('-check_in_time')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Currently Visiting Members',
            'visits': visits,
            'opts': self.model._meta,
            'current_view': 'current',
            'has_change_permission': self.has_change_permission(request),
        }
        return render(
            request,
            'admin/visits/visit/current_visits.html',
            context)

    def visit_history_view(self, request):
        # Get completed visits (has check-out time)
        visits = Visit.objects.filter(
            check_out_time__isnull=False
        ).order_by('-check_in_time')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Visit History',
            'visits': visits,
            'opts': self.model._meta,
            'current_view': 'history',
        }
        return render(
            request,
            'admin/visits/visit/visit_history.html',
            context)


# Register the model with the custom admin site
admin_site.register(Visit, VisitAdmin)
