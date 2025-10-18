from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Sözlükten anahtara göre değer döndürür."""
    try:
        return dictionary.get(key)
    except Exception:
        return None
