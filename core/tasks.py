from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost, Post
from .socialmedea_utils import generate_telegram_post, send_telegram_post , generate_device_post
from django.db import transaction
import random
from Medical_device.models import MedicalDevice
from celery import shared_task
import logging
logger = logging.getLogger(__name__)
from django.db import transaction

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
    Posts up to 5 unposted products for ONE supplier per cycle (round-robin),
    ensuring the entire posting and saving process is atomic.
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Last supplier that posted products
    last_post = SocialMediaPost.objects.filter(products__isnull=False).order_by("-post_date", "-id").first()
    last_index = suppliers.index(last_post.supplier) if last_post and last_post.supplier in suppliers else -1

    total_suppliers = len(suppliers)

    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        # Already posted product IDs
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, products__isnull=False
        ).values_list("products__id", flat=True)

        # Get unposted products
        products = Product.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5]

        if not products.exists():
            continue

        # Generate post
        post_text = generate_telegram_post(products)
        if not post_text:
            continue  # skip this supplier

        # Atomic block: send and save
        try:
            with transaction.atomic():
                # Send post first; raise exception if failed
                if not send_telegram_post(post_text):
                    raise Exception(f"Failed to send Telegram post for {supplier.name}")

                # Create SocialMediaPost and link products
                tg_post = SocialMediaPost(supplier=supplier, template_used=1, posted=True)
                tg_post.save()
                tg_post.products.add(*products)
                tg_post.save()

        except Exception as e:
            return f"❌ Posting failed for {supplier.name}: {e}"

        return f"✅ Posted {products.count()} products for {supplier.name}"

    # Reset if all products posted
    all_product_ids = set(Product.objects.values_list("id", flat=True))
    posted_product_ids = set(SocialMediaPost.objects.filter(products__isnull=False).values_list("products__id", flat=True))

    if all_product_ids <= posted_product_ids:
        SocialMediaPost.objects.filter(products__isnull=False).delete()
        return "🔄 All products exhausted. Cycle reset."

    return "⚠️ No products found to post."

def post_next_supplier_devices():
    """
    Posts up to 5 unposted devices for ONE supplier per cycle (round-robin).
    Tracks posted devices so each is posted only once until all are exhausted.
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Find the last supplier that posted devices
    last_post = SocialMediaPost.objects.filter(devices__isnull=False).order_by("-post_date", "-id").first()
    last_index = suppliers.index(last_post.supplier) if last_post and last_post.supplier in suppliers else -1

    total_suppliers = len(suppliers)

    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        # Collect all previously posted device IDs for this supplier
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, devices__isnull=False
        ).values_list("devices__id", flat=True)

        # Get up to 5 unposted devices
        devices = MedicalDevice.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5]

        if not devices.exists():
            continue  # try next supplier

        # Generate post text
        post_text = generate_device_post(devices)
        if not post_text:
            return f"⚠️ No post generated for {supplier.name}"

        # Send post
        if not send_telegram_post(post_text):
            return f"❌ Failed to send Telegram post for {supplier.name}"

        # Save post and link devices
        with transaction.atomic():
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used=2,
                post_date=today,
                posted=True,
            )
            tg_post.devices.set(devices)  # this links posted devices

        return f"✅ Posted {devices.count()} devices for {supplier.name}"

    # Check if all suppliers have no unposted devices
    all_devices_ids = set(MedicalDevice.objects.values_list("id", flat=True))
    posted_devices_ids = set(SocialMediaPost.objects.filter(devices__isnull=False).values_list("devices__id", flat=True))

    if all_devices_ids <= posted_devices_ids:
        # reset for next cycle
        SocialMediaPost.objects.filter(devices__isnull=False).delete()
        return "🔄 All devices exhausted. Cycle reset."

    return "⚠️ No devices found to post."
