import requests
import logging
import os,time
from .models import UserProducts
from dotenv import load_dotenv
import random, json
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
    """✨ Stock update From {supplier_name} 
🆕 Check out our latest arrivals!
{products_list}

💵 Attractive price 💵
🚚 Free & fast delivery

Or come to: {location}
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
    contact_info = "\n".join(contacts) if contacts else "Not available"

    # Template
    template = post_templates[0]
    city = getattr(supplier, "city", "") or ""
    address = getattr(supplier, "address", "") or ""
    location = f"{city} {address}".strip() if city or address else "Not specified"

    # Link to supplier products page
    obj = UserProducts.objects.filter(supplier=supplier).first()
    link_url = f"https://pharmagebeya.com/supplier-detail/{obj.id}/" if obj else "https://pharmagebeya.com/pharmaceutical-wholesalers/"
    catalog_url = "https://pharmagebeya.com/"

    text = template.format(
        supplier_name=supplier.name,
        products_list=products_list,
        contact_info=contact_info,
        location=location,
        link_url=link_url,
        catalog_url=catalog_url
    )

    # Build inline keyboard buttons
    keyboard_rows = [
        [
            {"text": "🌐 Visit Pharmagebeya", "url": "https://pharmagebeya.com"},
            {"text": "🛒 Visit Products", "url": link_url},
            {"text": "🔗 Copy Product Link", "url": link_url},
        ]
    ]

    contact_buttons = []
    if supplier.telegram_link:
        contact_buttons.append({"text": "💬 Telegram", "url": supplier.telegram_link})
    if supplier.whatsapp_link:
        if "wa.me" in supplier.whatsapp_link or "api.whatsapp.com" in supplier.whatsapp_link:
            whatsapp_url = supplier.whatsapp_link
        else:
            phone_clean = ''.join(filter(str.isdigit, supplier.whatsapp_link))
            whatsapp_url = f"https://wa.me/{phone_clean}" if phone_clean else None
        if whatsapp_url:
            contact_buttons.append({"text": "📱 WhatsApp", "url": whatsapp_url})
    if contact_buttons:
        keyboard_rows.append(contact_buttons)

    keyboard = {"inline_keyboard": keyboard_rows}

    return text, keyboard


def send_telegram_post(text, keyboard=None, retries=3, delay=2):
    """
    Sends a Telegram message with optional inline keyboard buttons.
    """
    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_BOT_ID")

    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing Telegram bot token or channel ID")
        return False

    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = keyboard

    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(base_url, json=payload, timeout=15)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("ok"):
                msg = "Telegram message with buttons" if keyboard else "Telegram text message"
                logger.info(f"{msg} sent successfully to channel {CHANNEL_ID}")
                return response_data
        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.warning(f"Attempt {attempt}/{retries} failed to send Telegram message: {e}")
            if attempt < retries:
                time.sleep(delay)

    logger.error(f"Failed to send Telegram message after {retries} attempts: {last_exception}")
    raise last_exception

def send_telegram_photo(devices, caption_text, reply_markup=None, retries=3, delay=2):
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
        logger.info(f"No image found for device '{first_device.name}'. Skipping Telegram photo post.")
        return False

    # Determine URL or local file
    img_field = first_image.image
    image_url = None
    use_local_file = False

    if hasattr(img_field, "path") and os.path.exists(img_field.path):
        image_url = img_field.path
        use_local_file = True
    elif hasattr(img_field, "url"):
        image_url = img_field.url
        if image_url.startswith("/"):
            site_url = getattr(settings, "SITE_URL", "")
            image_url = f"{site_url}{image_url}"

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
                    payload = {
                        "chat_id": CHANNEL_ID,
                        "caption": caption_text,
                        "parse_mode": "HTML",
                    }
                    if reply_markup:
                        payload["reply_markup"] = json.dumps(reply_markup)
                    response = requests.post(base_url_photo, data=payload, files=files, timeout=15)
            else:
                payload = {
                    "chat_id": CHANNEL_ID,
                    "photo": image_url,
                    "caption": caption_text,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    payload["reply_markup"] = json.dumps(reply_markup)
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
    """🩺 <b>{device_name}</b>{extra_str}{price_str}

✨ From <b>{supplier_name}</b>
📍 Location: {location}

"""
]

def generate_device_post(devices, post_templates=POST_TEMPLATES_PHOTO, as_caption=True):
    if not devices:
        return None, None, None

    # Take the first device only
    device = devices[0]
    supplier = device.supplier

    # Device basic info
    name_line = f"🩺 <b>{device.name}</b>"
    brand_line = f"🏷 Brand: {device.brand}" if device.brand else ""
    model_line = f"📦 Model: {device.model_number}" if device.model_number else ""
    intended_use_line = f"🎯 Intended Use: {device.intended_use}" if device.intended_use else ""
    description_line = f"📄 Description: {device.description[:300]}{'...' if device.description and len(device.description) > 300 else ''}" if device.description else ""

    # Location
    city = getattr(supplier, "city", "") or ""
    address = getattr(supplier, "address", "") or ""
    location = f"{city} {address}".strip() if (city or address) else "Not specified"

    # Links
    catalog_url = "https://pharmagebeya.com/list/device/"
    device_link = f"https://pharmagebeya.com/list/device/{device.id}/"

    # Build caption
    caption_parts = [
        name_line,
        brand_line,
        model_line,
        intended_use_line,
        description_line,
        f"📍 Location: {location}",
        f"🔗 <a href='{device_link}'>View Device</a>",
        f"📂 <a href='{catalog_url}'>More Devices</a>",
    ]
    caption_text = "\n".join([p for p in caption_parts if p])  # skip empty lines

    # Pick image
    image_url = None
    if hasattr(device, "images") and device.images.exists():
        first_image = device.images.first()
        image_url = first_image.image.url if hasattr(first_image.image, "url") else first_image.image

    # Inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🩺 View Device", "url": device_link},
                {"text": "📂 Explore More", "url": catalog_url},
            ],
            [
                {"text": "🔗 Visit Pharmagebeya", "url": "https://pharmagebeya.com"},
            ],
        ]
    }

    return caption_text, image_url, keyboard
