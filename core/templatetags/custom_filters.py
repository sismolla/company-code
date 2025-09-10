from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Returns the full URL with the given kwargs replaced in the GET query.
    """
    request = context['request']
    query = request.GET.dict()
    for key, value in kwargs.items():
        if value is not None:
            query[key] = value
        else:
            query.pop(key, None)
            
    # Remove the old 'page' parameter if a new one is set
    # This is a key part of solving your specific problem
    if 'page' in kwargs:
        query['page'] = kwargs['page']
        
    return '?' + '&'.join(f"{key}={value}" for key, value in query.items())