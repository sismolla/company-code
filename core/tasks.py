from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost, Post
from .socialmedea_utils import generate_telegram_post, send_telegram_post , generate_device_post, send_telegram_photo
from django.db import transaction
import random
from Medical_device.models import MedicalDevice
from celery import shared_task
import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Q # Import for more complex queries if needed

# Assuming these are defined elsewhere or passed in
# from .models import Supplier, SocialMediaPost, Product, MedicalDevice, DosageForm, Category, Attribute, ProductAttributeValue, ProductImage
# from Medical_device.models import ImpressionAggregate # This import is inside Product, might need adjustment

# Setup basic logging (replace with your actual Django logging configuration)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



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
    logger.info("Starting post_next_supplier_products cycle.")
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        logger.warning("No suppliers found to post products for.")
        return "⚠️ No suppliers found."

    # Last supplier that posted products
    last_post = SocialMediaPost.objects.filter(Q(products__isnull=False)).order_by("-post_date", "-id").first()
    last_index = -1
    if last_post and last_post.supplier in suppliers:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            logger.warning(f"Last posted supplier '{last_post.supplier.name}' not found in current supplier list.")

    total_suppliers = len(suppliers)

    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]
        logger.info(f"Attempting to process supplier: {supplier.name} (index: {next_index})")

        # Already posted product IDs for this supplier
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, products__isnull=False
        ).values_list("products__id", flat=True)

        # Get up to 5 unposted products
        products_to_post = Product.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5]

        if not products_to_post.exists():
            logger.info(f"No new products to post for {supplier.name}. Skipping.")
            continue

        # Generate post text + keyboard
        result = generate_telegram_post(products_to_post)
        if not result:
            logger.warning(f"Failed to generate post for {supplier.name}'s products. Skipping.")
            continue

        post_text, keyboard = result

        # Atomic block: Send post to Telegram AND save to database
        try:
            with transaction.atomic():
                logger.info(f"Entering atomic transaction for {supplier.name}'s products.")
                
                if not send_telegram_post(post_text, keyboard=keyboard):
                    raise Exception(f"send_telegram_post returned False for {supplier.name}'s products.")

                tg_post = SocialMediaPost(
                    supplier=supplier,
                    template_used=1,
                    posted=True,
                    post_date=today
                )
                tg_post.save()
                tg_post.products.set(products_to_post)
                tg_post.save()

                logger.info(f"✅ Successfully posted {products_to_post.count()} products for {supplier.name} and saved to DB.")
                
        except Exception as e:
            logger.error(f"Transaction failed for {supplier.name}'s products: {e}", exc_info=True)
            return f"❌ Posting failed for {supplier.name}: {e}"

        logger.info(f"Finished processing and posted for {supplier.name}.")
        return f"✅ Posted {products_to_post.count()} products for {supplier.name}"

    # --- Cycle Reset Logic ---
    logger.info("No suppliers had new products to post in this cycle. Checking for reset conditions.")
    all_product_ids = set(Product.objects.values_list("id", flat=True))
    posted_product_ids = set(
        SocialMediaPost.objects.filter(products__isnull=False)
        .values_list("products__id", flat=True)
    )

    if not all_product_ids:
        logger.info("No products exist in the database.")
        return "⚠️ No products exist in the database."

    if not posted_product_ids:
        logger.info("No products have been posted yet.")
        return "⚠️ No products have been posted yet."

    if all_product_ids == posted_product_ids:
        SocialMediaPost.objects.filter(products__isnull=False).delete()
        logger.info("All products exhausted and SocialMediaPost entries for products deleted. Cycle reset.")
        return "🔄 All products exhausted. Cycle reset."

    remaining = all_product_ids - posted_product_ids
    logger.info(f"Still {len(remaining)} products waiting to be posted across all suppliers.")
    return f"⏳ {len(remaining)} products still waiting to be posted."

def post_next_supplier_devices():
    """
    Posts up to 5 unposted devices for ONE supplier per cycle (round-robin),
    sending either a photo+caption or a plain text post,
    and saving everything atomically.
    """
    logger.info("Starting post_next_supplier_devices cycle.")
    today = timezone.now().date()
    suppliers = list(Supplier.objects.all().order_by("id"))

    if not suppliers:
        logger.warning("No suppliers found to post devices for.")
        return "⚠️ No suppliers found."

    # Last supplier that posted devices
    last_post = SocialMediaPost.objects.filter(Q(devices__isnull=False)).order_by("-post_date", "-id").first()
    last_index = -1
    if last_post and last_post.supplier in suppliers:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            logger.warning(f"Last posted supplier '{last_post.supplier.name}' not found in current supplier list.")

    total_suppliers = len(suppliers)

    for i in range(total_suppliers):
        next_index = (last_index + 1 + i) % total_suppliers
        supplier = suppliers[next_index]
        logger.info(f"Attempting to process supplier: {supplier.name} (index: {next_index})")

        # Already posted device IDs for this supplier
        posted_ids = SocialMediaPost.objects.filter(
            supplier=supplier, devices__isnull=False
        ).values_list("devices__id", flat=True)

        # Get up to 5 unposted devices
        devices_to_post = MedicalDevice.objects.filter(supplier=supplier).exclude(id__in=posted_ids)[:5]

        if not devices_to_post.exists():
            logger.info(f"No new devices to post for {supplier.name}. Skipping.")
            continue

        # Generate caption + image
        caption, image_url = generate_device_post(devices_to_post)

        if not caption:
            logger.warning(f"Failed to generate caption for {supplier.name}'s devices. Skipping.")
            continue

        # Atomic block: Send post to Telegram AND save to database
        try:
            with transaction.atomic():
                logger.info(f"Entering atomic transaction for {supplier.name}'s devices.")

                # Step 1: Send to Telegram (photo if image exists, else text)
                if image_url:
                    logger.info(f"Sending Telegram photo post for {supplier.name}.")
                    success = send_telegram_photo(devices_to_post, caption)  # <-- fixed here
                else:
                    logger.info(f"Sending Telegram text post for {supplier.name}.")
                    success = send_telegram_post(caption)

                if not success:
                    raise Exception(f"Telegram send failed for {supplier.name}'s devices.")

                # Step 2: Save post info in DB
                tg_post = SocialMediaPost(
                    supplier=supplier, template_used=2, posted=True, post_date=today
                )
                tg_post.save()
                tg_post.devices.add(*devices_to_post)
                tg_post.save()

                logger.info(f"Successfully posted {devices_to_post.count()} devices for {supplier.name} and saved to DB.")

        except Exception as e:
            logger.error(f"Transaction failed for {supplier.name}'s devices: {e}", exc_info=True)
            return f"❌ Posting failed for {supplier.name}: {e}"

        logger.info(f"Finished processing and posted for {supplier.name}.")
        return f"✅ Posted {devices_to_post.count()} devices for {supplier.name}"

    # --- Cycle Reset Logic ---
    logger.info("No suppliers had new devices to post in this cycle. Checking for reset conditions.")
    all_device_ids = set(MedicalDevice.objects.values_list("id", flat=True))
    posted_device_ids = set(
        SocialMediaPost.objects.filter(devices__isnull=False)
        .values_list("devices__id", flat=True)
    )

    if not all_device_ids:
        logger.info("No devices exist in the database.")
        return "⚠️ No devices exist in the database."

    if not posted_device_ids:
        logger.info("No devices have been posted yet.")
        return "⚠️ No devices have been posted yet."

    if all_device_ids == posted_device_ids:
        SocialMediaPost.objects.filter(devices__isnull=False).delete()
        logger.info("All devices exhausted and SocialMediaPost entries for devices deleted. Cycle reset.")
        return "🔄 All devices exhausted. Cycle reset."

    remaining = all_device_ids - posted_device_ids
    logger.info(f"Still {len(remaining)} devices waiting to be posted across all suppliers.")
    return f"⏳ {len(remaining)} devices still waiting to be posted."


#mrystockethiopia