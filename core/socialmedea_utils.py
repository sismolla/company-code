import requests
import logging
import os
from .models import UserProducts,Post,Platform
from dotenv import load_dotenv
import random
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
See full Supplier Products and order: {link_url}

🛒 Browse the complete catalog and order today: {catalog_url}
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

POST_TEMPLATES = [
    """🩺 {supplier_name} Medical Supplier
✨ Explore our top medical devices!
{device_list}

💵 Competitive prices 💵
🚚 Reliable nationwide delivery
{contact_info}
📍 Location: {location}

🔗 See full supplier details: {link_url}
🛒 Browse all medical devices and see there price: {catalog_url}
"""
]

def generate_device_post(devices, post_templates=POST_TEMPLATES):
    if not devices:
        return None

    supplier = devices[0].supplier

    # Prepare device list (4–7 items, or fewer if less available)
    count = min(len(devices), random.choice([4, 5, 6, 7]))
    device_list = ""
    for idx, p in enumerate(devices[:count], start=1):
        extra = []
        if p.brand:
            extra.append(p.brand)
        if p.model_number:
            extra.append(p.model_number)
        extra_str = f" ({', '.join(extra)})" if extra else ""
        price_str = f" - {p.price} ETB" if p.price else ""
        device_list += f"{idx}. {p.name}{extra_str}{price_str}\n"

    # Contact info
    contacts = []
    for attr in ["telegram_link", "whatsapp_link", "phone"]:
        value = getattr(supplier, attr, None)
        if value:
            contacts.append(f"{attr.replace('_link','').capitalize()}: {value}")
    contact_info = "\n".join(contacts) if contacts else "📞 Contact supplier directly."

    # Pick template
    template = post_templates[0]

    # Link to first device
    link_url = f"https://pharmagebeya.com/list/device/{devices[0].id}/"

    catalog_url = "https://pharmagebeya.com/list/device/"

    text = template.format(
        supplier_name=supplier.name,
        device_list=device_list,
        contact_info=contact_info,
        location=getattr(supplier, "address", "Not specified"),
        link_url=link_url,
        catalog_url=catalog_url,
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

def send_telegram_post(text):
    """
    Sends a Telegram message only to a channel.
    Raises exception if a request fails, so Celery can retry.
    """
    load_dotenv()
    channel_id = os.getenv("TELEGRAM_CHANNEL_BOT_ID")
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Send to the channel only
    payload_channel = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        response_channel = requests.post(base_url, json=payload_channel, timeout=10)
        response_channel.raise_for_status()
        logger.info(f"Telegram message sent to channel {channel_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message to channel {channel_id}: {e}")
        raise
