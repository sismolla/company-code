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
    Posts up to 5 unposted products for ONE supplier in round-robin order.
    - Only one supplier per run.
    - Posts multiple products from that supplier.
    - If all suppliers are exhausted, cycle resets.
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Find the last supplier who posted products
    last_post = SocialMediaPost.objects.filter(products__isnull=False).order_by("-post_date", "-id").first()
    last_index = suppliers.index(last_post.supplier) if last_post and last_post.supplier in suppliers else -1

    # Pick next supplier in round-robin
    next_index = (last_index + 1) % len(suppliers)
    supplier = suppliers[next_index]

    # Already posted product IDs for this supplier
    posted_ids = SocialMediaPost.objects.filter(
        supplier=supplier, products__isnull=False
    ).values_list("products__id", flat=True)

    # Get up to 5 new products for this supplier
    products = list(Product.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5])

    if not products:
        return f"⚠️ No un posted products left for {supplier.name}."

    # Generate post text
    post_text = generate_telegram_post(products)
    if not post_text:
        return f"⚠️ Failed to generate post for {supplier.name}."

    try:
        with transaction.atomic():
            if not send_telegram_post(post_text):
                raise Exception(f"Telegram post failed for {supplier.name}")

            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used=1,
                post_date=today,
                posted=True,
            )
            tg_post.products.set(products)

    except Exception as e:
        print(f"❌ Error posting for {supplier.name}: {e}")
        return f"❌ Failed posting for {supplier.name}."

    return f"✅ Posted {len(products)} products for {supplier.name}"


def post_next_supplier_devices():
    """
    Posts up to 5 unposted devices for ONE supplier in round-robin order.
    Ensures saving works properly (ManyToMany .set() instead of .add()).
    """
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # Last supplier that posted devices
    last_post = SocialMediaPost.objects.filter(devices__isnull=False).order_by("-post_date", "-id").first()
    last_index = suppliers.index(last_post.supplier) if last_post and last_post.supplier in suppliers else -1

    # Round-robin pick
    next_index = (last_index + 1) % len(suppliers)
    supplier = suppliers[next_index]

    # Already posted device IDs
    posted_ids = SocialMediaPost.objects.filter(
        supplier=supplier, devices__isnull=False
    ).values_list("devices__id", flat=True)

    # New devices to post
    devices = list(MedicalDevice.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5])

    if not devices:
        return f"⚠️ No unposted devices left for {supplier.name}."

    # Build post text
    post_text = generate_device_post(devices)
    if not post_text:
        return f"⚠️ Failed to generate post for {supplier.name}."

    try:
        with transaction.atomic():
            # Step 1: send Telegram
            if not send_telegram_post(post_text):
                raise Exception(f"Telegram post failed for {supplier.name}")

            # Step 2: Save DB record
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used=2,
                post_date=today,
                posted=True,
            )

            # Step 3: Link devices correctly
            tg_post.devices.set(devices)   # .set() ensures commit
            tg_post.save()

    except Exception as e:
        print(f"❌ Error posting for {supplier.name}: {e}")
        return f"❌ Failed posting for {supplier.name}"

    return f"✅ Posted {len(devices)} devices for {supplier.name}"
