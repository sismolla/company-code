from django import template

register = template.Library()

# templatetags/custom_filters.py
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
