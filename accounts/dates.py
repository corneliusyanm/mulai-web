"""Indonesian day and month names, in one place.

Every user-facing date on this site is read by an Indonesian member, so the words
belong somewhere every app can reach. They used to live in three copies:
`MONTHS_ID` in `accounts/views.py` for the chart labels, another `MONTHS_ID` in
`leaderboard/board.py`, and none at all in `indonesian_day()`, which is why the
class list headings and the WhatsApp invites said "30 August 2026".

Deliberately a leaf module with no imports, not even Django. It is pulled in by
views, by a template tag library and by the leaderboard, and anything it imported
could come back round as a circular import through one of those.

`gettext` is not used here on purpose. LANGUAGE_CODE is en-us and there is no
locale directory, so a `_("Senin")` never translated anything; it only looked
like the site had a translation layer it does not have.
"""

DAYS_ID = [
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
    "Minggu",
]

# Abbreviated for a calendar header, where seven full names will not fit. Same
# order as DAYS_ID, so both are indexed by date.weekday().
DAYS_ID_SHORT = [
    "Sen",
    "Sel",
    "Rab",
    "Kam",
    "Jum",
    "Sab",
    "Min",
]

MONTHS_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

MONTHS_ID_SHORT = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}


def day_name(date):
    """"Minggu"."""
    return DAYS_ID[date.weekday()]


def long_date(date):
    """"Minggu, 30 Agustus 2026". For a heading that carries the date."""
    return f"{day_name(date)}, {date.day} {MONTHS_ID[date.month]} {date.year}"


def short_date(date):
    """"Minggu, 30 Agu". For a line inside a sentence, where the year is noise."""
    return f"{day_name(date)}, {date.day} {MONTHS_ID_SHORT[date.month]}"


def day_month(date):
    """"30 Agu". For a parenthetical, where even the weekday is noise."""
    return f"{date.day} {MONTHS_ID_SHORT[date.month]}"


def day_month_year(date):
    """"30 Agu 2026". For a date a member may need to act on weeks later."""
    return f"{date.day} {MONTHS_ID_SHORT[date.month]} {date.year}"
