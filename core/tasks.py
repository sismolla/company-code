from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost
from .socialmedea_utils import generate_telegram_post, send_telegram_post , generate_device_post
from django.db import transaction
import random
from Medical_device.models import MedicalDevice

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
    Posts up to N unposted products for ONE supplier per cycle.
    - Goes supplier by supplier (round-robin).
    - If a supplier has no unposted products, skips to the next.
    - If all are exhausted, resets cycle.
    """

    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # ✅ Find the last supplier that posted
    last_post = SocialMediaPost.objects.order_by("-post_date", "-id").first()
    if last_post:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            last_index = -1
    else:
        last_index = -1  # no posts yet

    # Start from the next supplier
    total_suppliers = len(suppliers)
    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        # ✅ Check which products already posted
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier
        ).values_list("products__id", flat=True)

        # Fetch unposted products
        products = Product.objects.filter(supplier=supplier).exclude(
            id__in=posted_ids
        )[: random.choice([15, 20, 19, 25])]

        if not products.exists():
            continue  # skip to next supplier

        # ✅ Generate post content
        post_text = generate_telegram_post(products)
        if not post_text:
            return f"⚠️ No post generated for {supplier.name}"

        send_telegram_post(post_text)

        # ✅ Save to DB
        with transaction.atomic():
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used=1,
                post_date=today,
                posted=True,
            )
            tg_post.products.set(products)

        print(f"✅ Posted {products.count()} products for {supplier.name}")
        return f"Posted {products.count()} products for {supplier.name}"

    # 🔄 If we finish loop without posting, reset all
    print("✅ All suppliers exhausted. Resetting cycle.")
    first_supplier = suppliers[0]
    products = Product.objects.filter(supplier=first_supplier)[:5]
    if products.exists():
        post_text = generate_telegram_post(products)
        if post_text:
            send_telegram_post(post_text)
            with transaction.atomic():
                tg_post = SocialMediaPost.objects.create(
                    supplier=first_supplier,
                    template_used=1,
                    post_date=today,
                    posted=True,
                )
                tg_post.products.set(products)
            return f"Cycle restarted with {products.count()} products from {first_supplier.name}"

    return "No products available to restart cycle."

def post_next_supplier_devices():
    """
    Posts up to N unposted medical devices for ONE supplier per cycle.
    - Goes supplier by supplier (round-robin).
    - If supplier has no unposted devices, skips to next.
    - If all exhausted, restarts cycle.
    """

    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        return "⚠️ No suppliers found."

    # ✅ Last device post
    last_post = SocialMediaPost.objects.filter(devices__isnull=False).order_by("-post_date", "-id").first()

    if last_post:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            last_index = -1
    else:
        last_index = -1  # no device posts yet

    total_suppliers = len(suppliers)
    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]

        # ✅ Already posted device IDs
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier
        ).values_list("devices__id", flat=True)

        # Get unposted devices
        devices = MedicalDevice.objects.filter(supplier=supplier).exclude(
            id__in=posted_ids
        )[: random.choice([4, 5, 6, 7])]

        if not devices.exists():
            continue  # no unposted → skip supplier

        # ✅ Generate post text
        post_text = generate_device_post(devices)
        if not post_text:
            return f"⚠️ No post generated for {supplier.name}"

        send_telegram_post(post_text)

        # ✅ Save record
        with transaction.atomic():
            tg_post = SocialMediaPost.objects.create(
                supplier=supplier,
                template_used=1,
                post_date=today,
                posted=True,
            )
            tg_post.devices.set(devices)

        return f"✅ Posted {devices.count()} devices for {supplier.name}"

    # 🔄 All exhausted → reset with first supplier
    first_supplier = suppliers[0]
    devices = MedicalDevice.objects.filter(supplier=first_supplier)[:5]
    if devices.exists():
        post_text = generate_device_post(devices)
        if post_text:
            generate_device_post(post_text)
            with transaction.atomic():
                tg_post = SocialMediaPost.objects.create(
                    supplier=first_supplier,
                    template_used=1,
                    post_date=today,
                    posted=True,
                )
                tg_post.devices.set(devices)
            return f"🔄 Restarted cycle with {devices.count()} devices from {first_supplier.name}"

    return "⚠️ No devices available to restart cycle."
