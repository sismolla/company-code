from django.core.mail import send_mail
from django.conf import settings
import os
import smtplib
from django.core.mail import EmailMessage

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



def send_presentation_email(pharma_companies: dict, ppt_file_path: str):
    """
    Sends emails to all companies in the dictionary with personalized greetings.
    Skips invalid addresses but continues sending to others.
    """
    if not os.path.exists(ppt_file_path):
        print(f"Error: File {ppt_file_path} not found.")
        return

    subject = "Exclusive Opportunity: A First Look at the Pharmagebeya Platform"
    body_template = """
    Dear {company_name},

    I hope this email finds you well.

    As we are launching our new platform, Pharmagebeya, I wanted to share an exclusive presentation with you that outlines how our platform can significantly benefit your company and the wider pharmaceutical industry in Ethiopia.

    Our platform is a one-stop solution for pharmaceutical wholesalers and importers. It is designed to help you:
    - Expand your market reach and connect with a wider audience of buyers.
    - Streamline your operations by making it easy to manage your inventory and process orders.
    - Build your brand and become a recognized leader in the market.

    You will find the presentation attached to this email. It provides more detail on these benefits and our future plans for the platform.

    We are confident that Pharmagebeya will be a valuable asset to your business, and we look forward to exploring this opportunity with you.

    Best regards,  
    The Pharmagebeya Team
    """

    with open("send_log.txt", "a", encoding="utf-8") as log_file:
        for company_name, email_list in pharma_companies.items():
            for email in email_list:
                try:
                    msg = EmailMessage(
                        subject=subject,
                        body=body_template.format(company_name=company_name),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[email],
                    )
                    msg.attach_file(ppt_file_path)
                    msg.send(fail_silently=False)

                    log_file.write(f"✅ Sent to {email} ({company_name})\n")
                    print(f"✅ Sent to {email} ({company_name})")

                except smtplib.SMTPRecipientsRefused as e:
                    log_file.write(f"❌ Invalid email {email} ({company_name}) -> {e}\n")
                    print(f"❌ Invalid email {email} ({company_name}) -> {e}")

                except Exception as e:
                    log_file.write(f"⚠️ Failed to send to {email} ({company_name}) -> {e}\n")
                    print(f"⚠️ Failed to send to {email} ({company_name}) -> {e}")

    print("📨 Email sending process finished.")