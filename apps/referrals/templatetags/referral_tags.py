from django import template

register = template.Library()


@register.filter
def readable_key(value):
    """
    Convert a snake_case form-field key into a human-readable title string.

    Example: "first_name" → "First Name", "dob" → "Dob"

    Usage: {{ key|readable_key }}
    """
    return str(value).replace("_", " ").title()
