# notices/templatetags/poll_extras.py
from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """Returns the value from a dictionary using the provided key."""
    if isinstance(d, dict):
        return d.get(key)
    return None