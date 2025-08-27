from django.core.mail import send_mail
from django.conf import settings

from django.core.mail import send_mail
from django.conf import settings

def send_order_email(order):
    items_text = ""
    for item in order.items.all():
        items_text += f"- {item.product.name} x {item.quantity} -{item.product.dosage_form} birr {item.price} each = {item.get_total()}\n"

    message = f"""
Hi {order.customer_full_name},

Your order #{order.id} has been placed successfully! 🎉

Order details:
{items_text}

Delivery address: {order.customer_delivery_address}
Supplier: {order.supplier.name}
Supplier Address: {order.supplier.address}
Please catch with the wholesaler before the order lifetime is done (7 days).

Thank you for using Pharmagebeya!
"""

    send_mail(
        "Order Confirmation",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.customer_email_address],
    )



def notify_user(order, status):
    # Get first 3 products from order (assuming you have order.items relation)
    products = order.items.all()[:3]  # adjust based on your model
    product_list = "\n".join([f"- {item.product.name} ({item.quantity} pcs)" for item in products])
    total_items = order.items.count()

    # If more than 3 items, indicate additional products
    if total_items > 3:
        product_list += f"\n...and {total_items - 3} more items."

    subject = f"Order #{order.id} - {status}"
    message = f"""
Hello {order.customer_full_name},

Your order #{order.id} has been {status} by {order.supplier.name}.

Here are some of the items from your order:
{product_list}

We will keep you updated about the progress of your order.
If you have any questions, feel free to contact us.

Thank you for choosing us,
{order.supplier.name}
"""

    send_mail(
        subject,
        message.strip(),
        settings.DEFAULT_FROM_EMAIL,
        [order.customer_email_address],
    )
