from django.conf import settings


def debug_context(request):
    """Expose DEBUG setting to templates for conditional rendering."""
    return {"DEBUG": settings.DEBUG}
