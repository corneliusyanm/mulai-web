"""What every page tells search engines and link previews about itself.

Kept apart from the homepage copy (content.py) because base.html reads this on
every page, admin included, through mulai_web.context_processors.seo.
"""

import logging

from django.templatetags.static import static

from . import business

logger = logging.getLogger(__name__)

# The picture WhatsApp, Instagram and Facebook show when a link is shared.
SHARE_IMAGE = "images/home/og.jpg"


def absolute_static(path):
    """https://mulaigym.id/static/..., or None when the file is not in the manifest.

    Production raises on a static path missing from the manifest. The share image
    is read on every page and the homepage is the deploy health check, so a lost
    file drops out with an error in the log instead of taking every page down.
    Tests walk the fixed paths so it never gets that far.
    """
    try:
        return business.SITE_URL + static(path)
    except ValueError:
        logger.error("Static file missing from the manifest: %s", path)
        return None
