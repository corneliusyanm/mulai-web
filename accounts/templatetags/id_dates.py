"""Indonesian dates for templates.

Thin filters over `accounts/dates.py`, which is where the words themselves live.
In `accounts` rather than `classes` because every app's templates need them: the
class list, the account page, the nutrition quiz. They used to sit in
`classes.templatetags.class_extras`, which meant a template about food loading a
library named after gym classes to print a date.

Four forms, differing only in how much they say. Pick the shortest one that still
answers the question the member is asking:

    indonesian_day        Minggu, 30 Agustus 2026   a heading that is the date
    indonesian_date       Minggu, 30 Agu            a date inside a sentence
    indonesian_full_date  30 Agu 2026               a row in a list of dates
    indonesian_day_month  30 Agu                    a bracket after a time
"""

from django import template

from accounts.dates import day_month, day_month_year, long_date, short_date

register = template.Library()


@register.filter
def indonesian_day(date):
    """"Minggu, 30 Agustus 2026"."""
    return long_date(date)


@register.filter
def indonesian_date(date):
    """"Minggu, 30 Agu"."""
    return short_date(date)


@register.filter
def indonesian_full_date(date):
    """"30 Agu 2026"."""
    return day_month_year(date)


@register.filter
def indonesian_day_month(date):
    """"30 Agu"."""
    return day_month(date)
