from django import template

register = template.Library()

@register.filter
def attr(obj, attr_name):
    """Safely gets attribute from object."""
    return getattr(obj, attr_name, "")
