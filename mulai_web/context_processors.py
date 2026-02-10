from datetime import date

from django.conf import settings


def debug_context(request):
    """Expose DEBUG, RAMADAN_MODE, and Ramadan date range to templates."""
    ctx = {
        "DEBUG": settings.DEBUG,
        "RAMADAN_MODE": settings.RAMADAN_MODE,
    }
    if settings.RAMADAN_MODE:
        ctx["RAMADAN_START"] = date.fromisoformat(settings.RAMADAN_START)
        ctx["RAMADAN_END"] = date.fromisoformat(settings.RAMADAN_END)
    return ctx
