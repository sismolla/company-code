import requests
import logging
import os,time
from .models import UserProducts
from dotenv import load_dotenv
import random
from django.conf import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORGANIZATION_URN = os.getenv("LINKEDIN_ORGANIZATION_URN")  # e.g. "urn:li:organization:123456"
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")  # e.g., '123456789012345'
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

POST_TEMPLATES = [
    """✨ {supplier_name} Pharmaceutical Import
🆕 Check out our latest arrivals!
{products_list}

💵 Attractive price 💵
🚚 Free & fast delivery
{contact_info}
Or come to: {location}
🔗 <a href="{catalog_url}">See full Supplier Products and order</a>

🔗 <a href="{catalog_url}">Browse full catalog</a>
"""
]

def generate_telegram_post(products, post_templates=POST_TEMPLATES):
    if not products:
        return None

    supplier = products[0].supplier

    # Prepare product list
    products_list = ""
    for idx, p in enumerate(products[:10], start=1):
        products_list += f"{idx}. {p.name} {p.strength} - {p.price} ETB\n"

    # Contact info
    contacts = []
    if supplier.telegram_link:
        contacts.append(f"Telegram: {supplier.telegram_link}")
    if supplier.whatsapp_link:
        contacts.append(f"WhatsApp: {supplier.whatsapp_link}")
    if supplier.phone:
        contacts.append(f"Phone: {supplier.phone}")
    contact_info = "\n".join(contacts)

    # Pick template
    template = post_templates[0]  # you can still random.choice(post_templates)

    # Link ID fallback
    obj = UserProducts.objects.filter(supplier=supplier).first()
    link_url = f"https://pharmagebeya.com/supplier-detail/{obj.id}/" if obj else "https://pharmagebeya.com/pharmaceutical-wholesalers/"

    catalog_url = "https://pharmagebeya.com/"

    text = template.format(
        supplier_name=supplier.name,
        products_list=products_list,
        contact_info=contact_info,
        location=supplier.address or "",
        link_url=link_url,
        catalog_url=catalog_url
    )
    return text


def send_telegram_post_old(text):
    """
    Sends a Telegram message to a supplier group and a channel.
    Raises exception if a request fails, so Celery can retry.
    """
    load_dotenv()
    channel_id = os.getenv("TELEGRAM_CHANNEL_BOT_ID")
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_BOT_ID")  # Use the passed-in link for the supplier

    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # 1. Send to the supplier's chat
    payload_supplier = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response_supplier = requests.post(base_url, json=payload_supplier, timeout=10)
        response_supplier.raise_for_status()
        logger.info(f"Telegram message sent to supplier {chat_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message to supplier {chat_id}: {e}")
        # Re-raise the exception so Celery's retry mechanism can take over
        raise

    # 2. Send to the channel's chat
    payload_channel = {
        'chat_id': channel_id,
        "text": text,
        'parse_mode': 'HTML',
    }

    try:
        response_channel = requests.post(base_url, json=payload_channel, timeout=10)
        response_channel.raise_for_status()
        logger.info(f"Telegram message sent to channel {channel_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message to channel {channel_id}: {e}")
        raise

def send_telegram_post(text, retries=3, delay=2):
    """
    Fallback: Sends a plain text Telegram message to the channel.
    """
    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_BOT_ID")

    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing Telegram bot token or channel ID")
        return False

    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}

    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(base_url, json=payload, timeout=15)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("ok"):
                logger.info(f"Telegram text message sent successfully to channel {CHANNEL_ID}")
                return response_data
        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.warning(f"Attempt {attempt}/{retries} failed to send Telegram text: {e}")
            if attempt < retries:
                time.sleep(delay)

    logger.error(f"Failed to send Telegram text after {retries} attempts: {last_exception}")
    raise last_exception


def send_telegram_photo(devices, caption_text, retries=3, delay=2):
    """
    Sends a Telegram photo with caption for the first image of the first device.
    If no image exists, logs info and quits (no text-only fallback).
    """
    if not devices:
        logger.warning("No devices provided for Telegram post.")
        return False

    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_BOT_ID")
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing Telegram bot token or channel ID")
        return False

    base_url_photo = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    first_device = devices[0]
    first_image = first_device.images.first() if hasattr(first_device, "images") else None

    if not first_image or not getattr(first_image, "image", None):
        logger.info(f"No image found for device '{first_device.name}'. Skipping Telegram post.")
        return False

    # Determine URL or local file
    img_field = first_image.image
    image_url = None
    use_local_file = False

    if hasattr(img_field, "path") and os.path.exists(img_field.path):
        image_url = img_field.path
        use_local_file = True
        logger.info(f"Using local file for device '{first_device.name}': {image_url}")
    elif hasattr(img_field, "url"):
        image_url = img_field.url
        if image_url.startswith("/"):
            site_url = getattr(settings, "SITE_URL", "")
            image_url = f"{site_url}{image_url}"
        logger.info(f"Using URL for device '{first_device.name}': {image_url}")

    if not image_url:
        logger.info(f"Image not accessible for device '{first_device.name}'. Skipping Telegram post.")
        return False

    # Send photo
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            if use_local_file:
                with open(image_url, "rb") as photo_file:
                    files = {"photo": photo_file}
                    payload = {"chat_id": CHANNEL_ID, "caption": caption_text, "parse_mode": "HTML"}
                    response = requests.post(base_url_photo, data=payload, files=files, timeout=15)
            else:
                payload = {"chat_id": CHANNEL_ID, "photo": image_url, "caption": caption_text, "parse_mode": "HTML"}
                response = requests.post(base_url_photo, data=payload, timeout=15)

            response.raise_for_status()
            resp_data = response.json()
            if resp_data.get("ok"):
                logger.info(f"Telegram photo post sent successfully to {CHANNEL_ID}")
                return True
            else:
                raise Exception(resp_data.get("description", "Unknown Telegram API error"))

        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)

    logger.error(f"Failed to send photo after {retries} attempts. Error: {last_exception}")
    return False


POST_TEMPLATES_PHOTO = [
    """🩺 {supplier_name}
✨ Explore our medical devices!
{device_list}

📍 {location}
{contact_info}

🔗 <a href="{catalog_url}">Browse full catalog</a>
"""
]

def generate_device_post(devices, post_templates=POST_TEMPLATES_PHOTO, as_caption=True):
    """
    Generates a Telegram caption and selects a device image if available.
    Only uses the first device's first image. If no image exists, returns None for image.
    
    Returns:
        tuple: (caption_text, image_url_or_None)
    """
    if not devices:
        return None, None

    supplier = devices[0].supplier

    count = min(len(devices), random.choice([3, 4, 5]))
    device_list = ""
    for idx, p in enumerate(devices[:count], start=1):
        extra = []
        if getattr(p, "brand", None):
            extra.append(p.brand)
        if getattr(p, "model_number", None):
            extra.append(p.model_number)
        extra_str = f" ({', '.join(extra)})" if extra else ""
        price_str = f" - {p.price} ETB" if getattr(p, "price", None) else ""
        device_list += f"{idx}. {p.name}{extra_str}{price_str}\n"

    # Contact info
    contacts = []
    for attr in ["telegram_link", "whatsapp_link", "phone"]:
        value = getattr(supplier, attr, None)
        if value:
            contacts.append(f"{attr.replace('_link','').capitalize()}: {value}")
    contact_info = "\n".join(contacts) if contacts else "📞 Contact supplier directly"

    # Template
    template = post_templates[0]

    catalog_url = "https://pharmagebeya.com/list/device/"
    caption_text = template.format(
        supplier_name=supplier.name,
        device_list=device_list,
        contact_info=contact_info,
        location=getattr(supplier, "address", "Not specified"),
        catalog_url=catalog_url,
    )

    # Pick image: only first device image
    image_url = None
    first_device = devices[0]
    if hasattr(first_device, "images") and first_device.images.exists():
        first_image = first_device.images.first()
        image_url = first_image.image.url if hasattr(first_image.image, "url") else first_image.image

    if as_caption:
        return caption_text, image_url
    else:
        return caption_text