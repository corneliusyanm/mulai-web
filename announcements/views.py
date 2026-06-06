from django.http import JsonResponse

from .models import Announcement


def active_announcements(request):
    """Return currently-live announcements as JSON for the public banner.

    Rendered client-side (not via context processor) so the banner stays fresh
    even on response-cached pages like the equipment list (``@cache_page``).
    """
    items = [
        {
            "id": a.id,
            "message": a.message,
            "level": a.level,
            # Included in the client-side dismiss key so editing a message
            # makes it reappear even within the same session.
            "updated_at": a.updated_at.isoformat(),
        }
        for a in Announcement.get_live()
    ]
    response = JsonResponse({"announcements": items})
    response["Cache-Control"] = "no-store"
    return response
