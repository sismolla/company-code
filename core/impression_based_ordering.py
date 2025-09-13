from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from .models import Product

def top_products(limit=10):
    return (
        Product.objects.annotate(
            impressions_count=F('impressions__impression_count')  # use GenericRelation field
        )
        .order_by('-impressions_count')[:limit]
    )
