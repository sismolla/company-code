from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost
from .socialmedea_utils import generate_telegram_post, send_telegram_post , generate_device_post
from django.db import transaction
import random
from Medical_device.models import MedicalDevice

from celery import shared_task
from django.utils import timezone
from .models import Post
import logging
logger = logging.getLogger(__name__)

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
    Posts up to 5 unposted products for ONE supplier per cycle (round-robin).
    - Finds the last supplier that posted.
    - Moves to the next supplier.
    - Posts their next 5 unposted products.
    - If all suppliers are exhausted, clears SocialMediaPost and restarts fresh.
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Find the last supplier that posted
    last_post = SocialMediaPost.objects.filter(products__isnull=False).order_by("-post_date", "-id").first()
    if last_post:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            last_index = -1
    else:
        last_index = -1  # nothing posted yet

    total_suppliers = len(suppliers)

    # Try each supplier in round-robin order
    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        # Already posted products
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, products__isnull=False
        ).values_list("products__id", flat=True)

        # Unposted products (max 5)
        products = Product.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:20]

        if not products.exists():
            continue  # skip to next supplier

        # Generate post
        post_text = generate_telegram_post(products)
        if not post_text:
            return f"⚠️ No post generated for {supplier.name}"

        # Send post
        success = send_telegram_post(post_text)
        if not success:
            return f"❌ Failed to send Telegram post for {supplier.name}"

        # Save to DB
        with transaction.atomic():
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used="product_template",
                post_date=today,
                posted=True,
            )
            tg_post.products.set(products)

        return f"✅ Posted {products.count()} products for {supplier.name}"

    # If no supplier had products left → reset cycle
    if SocialMediaPost.objects.exists():
        SocialMediaPost.objects.all().delete()
        return "🔄 All suppliers exhausted. Cycle reset."
    return "⚠️ No products found to post."

def post_next_supplier_devices():
    """
    Posts up to 5 unposted devices for ONE supplier per cycle (round-robin).
    Same logic as products, but for devices.
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Last device post
    last_post = SocialMediaPost.objects.filter(devices__isnull=False).order_by("-post_date", "-id").first()
    if last_post:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            last_index = -1
    else:
        last_index = -1

    total_suppliers = len(suppliers)

    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, devices__isnull=False
        ).values_list("devices__id", flat=True)

        devices = MedicalDevice.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5]

        if not devices.exists():
            continue

        post_text = generate_telegram_post(devices)
        if not post_text:
            return f"⚠️ No post generated for {supplier.name}"

        success = send_telegram_post(post_text)
        if not success:
            return f"❌ Failed to send Telegram post for {supplier.name}"

        with transaction.atomic():
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used="device_template",
                post_date=today,
                posted=True,
            )
            tg_post.devices.set(devices)

        return f"✅ Posted {devices.count()} devices for {supplier.name}"

    # Reset if exhausted
    if SocialMediaPost.objects.exists():
        SocialMediaPost.objects.all().delete()
        return "🔄 All suppliers exhausted. Cycle reset."
    return "⚠️ No devices found to post."
