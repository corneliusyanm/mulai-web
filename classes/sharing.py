"""The "Ajak Temen" WhatsApp invite for a class.

One function, because the invite goes out from two places (the class detail page
and the member's own upcoming list on /akun) and the two must not drift into
saying different things about the same class.
"""

from urllib.parse import quote

from .templatetags.class_extras import indonesian_day


def whatsapp_invite_url(instance, detail_url):
    text = (
        f"Yuk ikut kelas {instance.class_schedule.class_obj.name} di Mulai Gym, "
        f"{indonesian_day(instance.date)} jam "
        f"{instance.start_time.strftime('%H:%M')}. "
        f"Detailnya di sini: {detail_url}"
    )
    return f"https://wa.me/?text={quote(text)}"
