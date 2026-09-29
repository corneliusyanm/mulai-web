"""Store every member's number the way almost all of them already are: 62812...

18 members in production were stored as "0812...", "ID812..." or "8210...",
typed that way into the admin. The login box finds them either way now
(`phone_candidates()` in accounts/forms.py), but staff searches, exports and
WhatsApp links all expect "62...".

A row is left alone when its new form would be shorter than a real number, or
would clash with another member's number (none did when this was written),
since two members on one number is a question for a human, not a migration.
There is no way back: the old spelling carried no information worth keeping.
"""

from collections import Counter

from django.db import migrations

MIN_PHONE_DIGITS = 9


def _as_62(raw):
    # A frozen copy of accounts.forms.member_style_phone, so this migration
    # keeps doing the same thing if that function ever changes.
    digits = "".join(ch for ch in raw or "" if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("620"):
        digits = "62" + digits[3:]
    elif digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return digits


def forwards(apps, schema_editor):
    Member = apps.get_model("accounts", "Member")
    rows = list(Member.objects.values_list("id", "phone_number"))
    in_use = Counter(phone for _, phone in rows)
    wanted = Counter(_as_62(phone) for _, phone in rows if _as_62(phone) != phone)

    for member_id, phone in rows:
        new = _as_62(phone)
        if new == phone or len(new) < MIN_PHONE_DIGITS:
            continue
        if in_use[new] or wanted[new] > 1:
            continue
        Member.objects.filter(pk=member_id).update(phone_number=new)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0023_masukkan_topic"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
