from django import template
from django.utils import timezone
from django.utils.timezone import localtime

register = template.Library()


@register.filter
def jakarta_time(value):
    if value:
        local_dt = localtime(value)
        return local_dt.strftime("%d %b %Y %H:%M")
    return ""


@register.filter
def format_phone(value):
    """Add a '+' prefix to phone numbers."""
    if value:
        # Ensure we're working with a string
        value = str(value)
        # If it already has a plus sign, return as is
        if value.startswith("+"):
            return value
        # Otherwise, add the plus sign
        return "+" + value
    return ""
