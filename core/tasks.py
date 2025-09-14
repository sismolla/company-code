from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost
from .socialmedea_utils import generate_telegram_post, send_telegram_post
from django.db import transaction


from celery import shared_task
from django.utils import timezone
from .models import Post

@shared_task
def post_to_telegram():
    posts = Post.objects.filter(platform__icontains="telegram", posted=False)
    for post in posts:
        if post.approved:
            try:
                send_telegram_post(post.content)
                post.posted = True
                post.save()
            except Exception as e:
                print(f"Failed: {e}")

def post_next_supplier_products():
    """
    Posts up to 20 unposted products PER SUPPLIER in round-robin order.
    - Goes supplier by supplier, posting 20 each time.
    - If all suppliers have no unposted products left, resets and starts again.
    """
    today = timezone.now().date()
    suppliers = Supplier.objects.all().order_by("id")

    any_posted = False

    # Loop through all suppliers
    for supplier in suppliers:
        try:
            # ✅ Get all products ever posted for this supplier
            posted_product_ids = SocialMediaPost.objects.filter(
                supplier=supplier
            ).values_list("products__id", flat=True)

            # Fetch next 20 unposted
            products = Product.objects.filter(supplier=supplier).exclude(
                id__in=posted_product_ids
            )[:20]

            if not products.exists():
                continue  # No unposted left for this supplier

            # ✅ Post found products
            post_text = generate_telegram_post(products)
            if not post_text:
                print(f"No post generated for {supplier.name}")
                continue

            send_telegram_post(post_text)

            # Save to DB
            with transaction.atomic():
                tg_post = SocialMediaPost.objects.create(
                    supplier=supplier,
                    template_used=1,
                    post_date=today,
                    posted=True,
                )
                tg_post.products.set(products)

            print(f"Posted {products.count()} products for {supplier.name}")
            any_posted = True

        except Exception as e:
            print(f"Error posting for {supplier.name}: {e}")
            continue

    # 🔄 If no unposted products found for any supplier, reset cycle
    if not any_posted:
        print("✅ All products posted. Restarting cycle from first supplier.")
        for supplier in suppliers:
            products = Product.objects.filter(supplier=supplier).order_by("id")[:20]
            if products.exists():
                post_text = generate_telegram_post(products)
                if post_text:
                    send_telegram_post(post_text)
                    with transaction.atomic():
                        tg_post = SocialMediaPost.objects.create(
                            supplier=supplier,
                            template_used=1,
                            post_date=today,
                            posted=True,
                        )
                        tg_post.products.set(products)
                    print(f"Restarted posting {products.count()} products for {supplier.name}")
        return "Cycle restarted."

    return "Finished posting for this run."

