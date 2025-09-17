from django.utils import timezone
from .models import Supplier, Product, SocialMediaPost, Post
from .socialmedea_utils import generate_telegram_post, send_telegram_post , generate_device_post
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
    # Using Q objects for robustness if devices/products could both be null
    last_post = SocialMediaPost.objects.filter(Q(products__isnull=False)).order_by("-post_date", "-id").first()
    
    last_index = -1
    if last_post and last_post.supplier in suppliers:
        try:
            last_index = suppliers.index(last_post.supplier)
        except ValueError:
            # Supplier from last_post no longer exists or is not in the current list
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

        # Generate post text
        post_text = generate_telegram_post(products_to_post)
        if not post_text:
            logger.warning(f"Failed to generate post text for {supplier.name}'s products. Skipping.")
            continue # skip this supplier

        # Atomic block: Send post to Telegram AND save to database
        try:
            with transaction.atomic():
                logger.info(f"Entering atomic transaction for {supplier.name}'s products.")
                
                # Step 1: Send the post to Telegram
                # This call *must* accurately reflect success/failure.
                if not send_telegram_post(post_text):
                    # If send_telegram_post returns False, we raise an exception
                    # to trigger a rollback and prevent DB update.
                    raise Exception(f"send_telegram_post returned False for {supplier.name}'s products.")

                # Step 2: If Telegram post was successful, save to database
                tg_post = SocialMediaPost(supplier=supplier, template_used=1, posted=True, post_date=today)
                tg_post.save()
                tg_post.products.set(products_to_post)
                # The second tg_post.save() is not strictly necessary after .set()
                # as .set() operates on the M2M manager, which typically saves directly.
                # However, leaving it doesn't hurt and ensures any other fields are persisted.
                tg_post.save() 
                logger.info(f"Successfully posted {products_to_post.count()} products for {supplier.name} and saved to DB.")
                
        except Exception as e:
            logger.error(f"Transaction failed for {supplier.name}'s products: {e}", exc_info=True)
            return f"❌ Posting failed for {supplier.name}: {e}"

        logger.info(f"Finished processing and posted for {supplier.name}.")
        return f"✅ Posted {products_to_post.count()} products for {supplier.name}"

    # --- Cycle Reset Logic (if no products were posted for any supplier) ---
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
    ensuring the entire posting and saving process is atomic.
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

        # Generate post text
        post_text = generate_device_post(devices_to_post)
        if not post_text:
            logger.warning(f"Failed to generate post text for {supplier.name}'s devices. Skipping.")
            continue # skip this supplier

        # Atomic block: Send post to Telegram AND save to database
        try:
            with transaction.atomic():
                logger.info(f"Entering atomic transaction for {supplier.name}'s devices.")
                
                # Step 1: Send the post to Telegram
                if not send_telegram_post(post_text):
                    raise Exception(f"send_telegram_post returned False for {supplier.name}'s devices.")

                # Step 2: If Telegram post was successful, save to database
                tg_post = SocialMediaPost(supplier=supplier, template_used=2, posted=True, post_date=today)
                tg_post.save()
                tg_post.devices.add(*devices_to_post) # Use add for multiple instances
                tg_post.save() # Optional, but harmless
                logger.info(f"Successfully posted {devices_to_post.count()} devices for {supplier.name} and saved to DB.")

        except Exception as e:
            logger.error(f"Transaction failed for {supplier.name}'s devices: {e}", exc_info=True)
            return f"❌ Posting failed for {supplier.name}: {e}"
        
        logger.info(f"Finished processing and posted for {supplier.name}.")
        return f"✅ Posted {devices_to_post.count()} devices for {supplier.name}"

    # --- Cycle Reset Logic (if no devices were posted for any supplier) ---
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
