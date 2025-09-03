import requests
import logging
import os
from .models import UserProducts,Post,Platform
from dotenv import load_dotenv
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
    link_url = f"http://127.0.0.1:8000/pharmacy/supplier-detail/{obj.id}/" if obj else "http://127.0.0.1:8000/pharmacy/"

    catalog_url = "http://127.0.0.1:8000/pharmacy/"

    text = template.format(
        supplier_name=supplier.name,
        products_list=products_list,
        contact_info=contact_info,
        location=supplier.address or "",
        link_url=link_url,
        catalog_url=catalog_url
    )
    return text

def send_telegram_post(text):
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


def send_linkedin_post(content: str):
    """
    Post text content to LinkedIn page (organization) only.

    Args:
        content (str): The text content of the post.
    """
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    post_data = {
        "author": LINKEDIN_ORGANIZATION_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_data
    )

    if response.status_code == 201:
        print("LinkedIn post created successfully!")
    else:
        print("Failed to post to LinkedIn:", response.status_code, response.text)
        response.raise_for_status()

def send_facebook_post(content: str, image_url: str = None):
    """
    Post to Facebook Page. Supports optional image.
    """
    if image_url:
        # Image post
        url = f"https://graph.facebook.com/v17.0/{FACEBOOK_PAGE_ID}/photos"
        payload = {
            "caption": content,
            "url": image_url,  # publicly accessible image URL
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }
    else:
        # Text-only post
        url = f"https://graph.facebook.com/v17.0/{FACEBOOK_PAGE_ID}/feed"
        payload = {
            "message": content,
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }

    response = requests.post(url, data=payload)
    if response.status_code in [200, 201]:
        print("Facebook post created successfully!")
    else:
        print("Failed to post to Facebook:", response.status_code, response.text)
        response.raise_for_status()




def send_instagram_post(content: str, image_url: str):
    """
    Post an image with caption to Instagram Business account.
    """
    # Step 1: Create media container
    create_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_USER_ID}/media"
    payload = {
        "image_url": image_url,  # public URL of the image
        "caption": content,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(create_url, data=payload)
    response.raise_for_status()
    creation_id = response.json().get("id")

    if not creation_id:
        raise Exception("Failed to create Instagram media container")

    # Step 2: Publish
    publish_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_USER_ID}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(publish_url, data=payload)
    if response.status_code in [200, 201]:
        print("Instagram post created successfully!")
    else:
        print("Failed to post to Instagram:", response.status_code, response.text)
        response.raise_for_status()
