from django import template
from urllib.parse import urlencode, parse_qs

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Returns the current URL's query string updated with the provided kwargs.
    
    Usage in template:
        {% url_replace page=2 category='Oral' %}
        
    - If value is None, the parameter is removed from the query string.
    - Preserves all other GET parameters.
    - Handles multiple values for the same key.
    """
    request = context['request']
    
    # Get current GET parameters as a mutable dict with lists for multiple values
    query = parse_qs(request.META.get('QUERY_STRING', ''), keep_blank_values=True)
    
    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            # Always store as a list to preserve multi-value parameters
            query[key] = [str(value)]
    
    # Encode query string safely
    return '?' + urlencode(query, doseq=True)


@register.filter
def round_count(value):
    """
    Round the number to nearest 10, 50, 100, or 1000 for display.
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value

    if value < 10:
        return value
    elif value < 100:
        return (value + 9) // 10 * 10
    elif value < 1000:
        return ((value + 49) // 50 * 50)
    else:
        return ((value + 999) // 1000 * 1000)
