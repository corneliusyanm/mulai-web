from datetime import date

from django.conf import settings

from homepage import business
from homepage.seo import SHARE_IMAGE, absolute_static

DEFAULT_DESCRIPTION = (
    "Mulai Gym, gym yang nyaman dan ramah buat pemula di Bandung. "
    f"{business.STREET}, {business.LANDMARK_MID_SENTENCE}."
)


def seo(request):
    """What base.html needs for the canonical link and the social preview.

    The canonical URL is always the bare https://mulaigym.id address, whichever
    host the request came in on: www.mulaigym.id serves the same pages without
    redirecting, and without this Google sees two copies of every page.
    """
    return {
        "SITE_URL": business.SITE_URL,
        "canonical_url": business.SITE_URL + request.path,
        "DEFAULT_DESCRIPTION": DEFAULT_DESCRIPTION,
        # None if the file ever goes missing: the page loses its preview, not its 200
        "SHARE_IMAGE_URL": absolute_static(SHARE_IMAGE),
        "WHATSAPP_URL": business.whatsapp_url(),
    }


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
