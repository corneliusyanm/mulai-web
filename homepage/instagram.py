"""Instagram tiles for the homepage grid.

Kept in code, not in the database, because the images ship with the deploy
(``static/images/instagram/``) so a new tile needs a deploy anyway. Same shape
as ``JOB_LISTINGS`` in ``accounts/views.py``.

Not pulled from Instagram: the Basic Display API was shut down at the end of
2024, and the Graph API replacement still hands back CDN URLs that expire within
hours, so the files would have to be hosted here regardless. Picking the tiles by
hand also keeps announcements and reposts out of the grid.

To add a tile:
  1. Put a square image (1080x1080 is plenty, compress it) in
     ``static/images/instagram/``.
  2. Add an entry below. ``alt`` is what a screen reader reads out, so describe
     the photo, not the post. ``post_url`` is optional; without it the tile links
     to the profile.
  3. Bump the CSS cache-buster only if you touched the stylesheet.

The section hides itself when this list is empty.

Mind the path: production serves static files through
``CompressedManifestStaticFilesStorage``, where ``{% static %}`` on a file that
is not in the manifest **raises**, so one typo here would take the whole
homepage down with a 500. ``get_tiles()`` drops entries whose file cannot be
found so that can't happen, and a test fails loudly on a bad path before it ever
reaches a deploy.
"""

import logging

from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

INSTAGRAM_PROFILE_URL = "https://instagram.com/mulaigym.id"

INSTAGRAM_TILES = [
    # {
    #     "image": "images/instagram/01.jpg",
    #     "alt": "Member latihan dada di bench press",
    #     "post_url": "https://www.instagram.com/p/XXXXXXXXXXX/",
    # },
]


GRID_SIZE = 9


def get_tiles():
    """Tiles to render: capped to a tidy 3 x 3, and only ones whose file exists.

    A missing file would otherwise raise inside ``{% static %}`` under manifest
    storage and take the homepage down. Losing one tile is a much better failure
    than losing the page.
    """
    tiles = []
    for tile in INSTAGRAM_TILES[:GRID_SIZE]:
        if finders.find(tile["image"]):
            tiles.append(tile)
        else:
            logger.warning("Instagram tile skipped, file not found: %s", tile["image"])
    return tiles
