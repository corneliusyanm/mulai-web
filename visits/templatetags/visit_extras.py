from django import template
from django.utils import timezone
from django.utils.timezone import localtime

register = template.Library()


@register.filter
def jakarta_time(value):
    if value:
        local_dt = localtime(value)
        return local_dt.strftime("%d %b %Y %H:%M")
    return ''
