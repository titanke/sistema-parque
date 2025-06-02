from django import template

register = template.Library()

@register.filter
def punto_decimal(value):
    try:
        return f"{float(value):,.2f}"
    except:
        return value
