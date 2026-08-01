"""Build an .ics file for a class instance, so a member can drop the class into
their phone calendar and get a reminder from the calendar app itself.

Hand-rolled on purpose: one VEVENT does not justify a dependency. Follows
RFC 5545 for the parts that matter (CRLF endings, escaping, 75-octet folding,
UTC timestamps).
"""

from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

GYM_LOCATION = "Mulai Gym, Jl. Jend. Sudirman No.643, Bandung"
REMINDER_MINUTES = 60


def _escape(text):
    """Escape a TEXT value: backslash, semicolon, comma, newline (RFC 5545 3.3.11)."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line):
    """Split a content line at 75 octets, continuation lines start with a space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    chunks = []
    start = 0
    limit = 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        # Don't split in the middle of a multi-byte character
        while end > start and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(raw[start:end].decode("utf-8"))
        start = end
        limit = 74  # continuation lines lose one octet to the leading space
    return "\r\n ".join(chunks)


def _utc_stamp(value):
    return value.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def class_instance_to_ics(instance, url=None, now=None):
    """One VCALENDAR with one VEVENT for `instance`, as a string.

    Times are written in UTC (the trailing Z form), which every calendar app
    reads correctly without needing a VTIMEZONE block.
    """
    class_name = instance.class_schedule.class_obj.name
    start = timezone.make_aware(datetime.combine(instance.date, instance.start_time))
    end = timezone.make_aware(datetime.combine(instance.date, instance.end_time))

    description = f"Kelas {class_name} di Mulai Gym."
    if url:
        description = f"{description} Detail kelas: {url}"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mulai Gym//Jadwal Kelas//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:kelas-{instance.id}@mulaigym.id",
        f"DTSTAMP:{_utc_stamp(now or timezone.now())}",
        f"DTSTART:{_utc_stamp(start)}",
        f"DTEND:{_utc_stamp(end)}",
        f"SUMMARY:{_escape(f'{class_name} - Mulai Gym')}",
        f"DESCRIPTION:{_escape(description)}",
        f"LOCATION:{_escape(GYM_LOCATION)}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        f"TRIGGER:-PT{REMINDER_MINUTES}M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape(f'{class_name} mulai 1 jam lagi')}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def ics_filename(instance):
    name = instance.class_schedule.class_obj.name.lower().replace(" ", "-")
    safe_name = "".join(char for char in name if char.isalnum() or char == "-")
    return f"{safe_name}-{instance.date:%Y-%m-%d}.ics"
