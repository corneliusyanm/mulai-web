"""The gym's public facts: where it is, when it is open, how to reach it.

One place for all of them, because the same facts show up in the homepage copy,
in the structured data Google reads, and in the Jam Kosong strip on /akun. Three
copies of the opening hours would eventually disagree, and the one that drifted
would be the one a member drove over for.

A leaf module on purpose: nothing but the standard library, so any app can import
it without an import cycle.
"""

from datetime import time
from urllib.parse import quote

NAME = "Mulai Gym"
SITE_DOMAIN = "mulaigym.id"
SITE_URL = f"https://{SITE_DOMAIN}"

STREET = "Jl. Jend. Sudirman No. 643"
# For places with no room for the full form, like the Google snippet.
STREET_SHORT = "Jl. Sudirman 643"
CITY = "Bandung"
REGION = "Jawa Barat"
# As the Google Maps listing writes it. Matching the listing word for word is
# part of what local search uses to tie this site to that pin.
KELURAHAN = "Warung Muncang"
KECAMATAN = "Bandung Kulon"
POSTAL_CODE = "40211"
AREA_LINE = f"{KELURAHAN}, Kec. {KECAMATAN}, {CITY} {POSTAL_CODE}"
LANDMARK = "Seberang SMPK 5 BPK Penabur"
# The same, halfway through a sentence. Only the first letter changes: SMPK stays SMPK.
LANDMARK_MID_SENTENCE = LANDMARK[0].lower() + LANDMARK[1:]

# From the Google Maps listing (the pin, not the map centre).
LATITUDE = -6.9178955
LONGITUDE = 107.5774546
MAPS_URL = "https://maps.app.goo.gl/NGSqB9qy22e1Zssk8"
MAPS_EMBED_URL = (
    "https://www.google.com/maps?output=embed&z=17&q="
    + quote(f"{NAME}, {STREET}, {CITY}")
)

# Digits only, the way wa.me wants it.
WHATSAPP_NUMBER = "628996940908"
PHONE_DISPLAY = "0899-6940-908"
PHONE_INTERNATIONAL = "+62-899-6940-908"

INSTAGRAM_URL = "https://www.instagram.com/mulaigym.id/"
TIKTOK_URL = "https://www.tiktok.com/@mulaigym.id"
FACEBOOK_URL = "https://www.facebook.com/61575724376452/"

# Python weekday() (Monday=0) -> (opens, closes). Sunday opens half an hour late.
OPENING_TIMES = {
    0: (time(7, 0), time(21, 0)),
    1: (time(7, 0), time(21, 0)),
    2: (time(7, 0), time(21, 0)),
    3: (time(7, 0), time(21, 0)),
    4: (time(7, 0), time(21, 0)),
    5: (time(7, 0), time(20, 0)),
    6: (time(7, 30), time(20, 0)),
}

DAY_NAMES_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
DAY_NAMES_SCHEMA = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# Where members actually live, from the address they gave at signup, most common
# first. Named on the page because "gym dekat Cijerah" is how people search.
NEARBY_AREAS = [
    "Andir", "Cijerah", "Pagarsih", "Garuda", "Rajawali", "Holis", "Kopo", "Cimahi",
]


def nearby_areas_text():
    """The areas as one phrase: Andir, Cijerah, ..., Kopo, sampai Cimahi."""
    return ", ".join(NEARBY_AREAS[:-1]) + f", sampai {NEARBY_AREAS[-1]}"


def whatsapp_url(text=""):
    """A wa.me link to the front desk, optionally with a message already typed."""
    url = f"https://wa.me/{WHATSAPP_NUMBER}"
    return f"{url}?text={quote(text)}" if text else url


def opening_hours_rows():
    """Consecutive days with the same hours folded into one row.

    [("Senin - Jumat", "07:00 - 21:00"), ("Sabtu", "07:00 - 20:00"), ...]
    """
    rows = []
    for day in range(7):
        opens, closes = OPENING_TIMES[day]
        hours = f"{opens:%H:%M} - {closes:%H:%M}"
        if rows and rows[-1]["hours"] == hours:
            rows[-1]["last"] = day
        else:
            rows.append({"first": day, "last": day, "hours": hours})
    return [
        (
            DAY_NAMES_ID[r["first"]]
            if r["first"] == r["last"]
            else f"{DAY_NAMES_ID[r['first']]} - {DAY_NAMES_ID[r['last']]}",
            r["hours"],
        )
        for r in rows
    ]
