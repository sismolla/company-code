from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost
from .telegram_utils import generate_telegram_post, send_telegram_post
import logging
from django.db import transaction

def post_next_supplier_products():
    """
    Posts unposted products for **one supplier** per run to Telegram.
    Retries up to 3 times if Telegram API fails.
    """
    today = timezone.now().date()
    # Loop through suppliers in order
    for supplier in Supplier.objects.all().order_by("id"):
        try:
            # Check for unposted products
            posted_product_ids = SocialMediaPost.objects.filter(supplier=supplier ,post_date=today).values_list('products__id', flat=True)
            products = Product.objects.filter(supplier=supplier).exclude(id__in=posted_product_ids)[:20]

            if not products.exists():
                continue  # Move to next supplier

            # Generate post
            post_text = generate_telegram_post(products)
            if not post_text:
                print(f"No post generated for supplier {supplier.name}")
                continue

            # Send to Telegram
            send_telegram_post(post_text)

            # Record post
            with transaction.atomic():
                tg_post = SocialMediaPost.objects.create(
                    supplier=supplier,
                    template_used=1,
                    post_date=today,
                    posted=True
                )
                tg_post.products.set(products)
            tg_post.save()

            print(f"Posted {products.count()} products for {supplier.name}")

            # **Stop after posting one supplier per run**
            return f"Posted {products.count()} products for {supplier.name}"

        except Exception as e:
            print(f"Error posting for supplier {supplier.name}: {e}")
            try:
                self.retry(exc=e)
            except self.MaxRetriesExceededError:
                print(f"Max retries exceeded for supplier {supplier.name}")

    print("No suppliers with unposted products today.")
    return "No suppliers with unposted products found today."
