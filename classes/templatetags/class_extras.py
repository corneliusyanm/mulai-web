from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def indonesian_day(date):
    day_names = [
        _("Senin"),
        _("Selasa"),
        _("Rabu"),
        _("Kamis"),
        _("Jumat"),
        _("Sabtu"),
        _("Minggu"),
    ]
    return f"{day_names[date.weekday()]}, {date.strftime('%d %B %Y')}"
