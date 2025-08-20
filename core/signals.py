from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ReportAbuse, Notification  # import your models
# from django.core.mail import send_mail

@receiver(post_save, sender=ReportAbuse)
def notify_seller_on_abuse_report(sender, instance, created, **kwargs):
    if created:
        product = instance.product
        seller = product.supplier   # assuming `supplier` is related to user or has contact info
        # Example: send email notification
        # if seller.email:
        #     subject = f"Abuse Report Received for Your Product: {product.name}"
        #     message = (
        #         f"Hello {seller.name},\n\n"
        #         f"Your product '{product.name}' has been reported for abuse.\n"
        #         f"Reason: {instance.get_reason_display()}\n"
        #         f"Description: {instance.description}\n\n"
        #         "Please review and take necessary action."
        #     )
        #     # send_mail(subject, message, 'no-reply@yourdomain.com', [seller.email])

        if seller:
             Notification.objects.create(
                recipient=seller.user,
                message=f"Your product '{product.name}' has been reported. "
                f"Main reason: '{instance.get_reason_display()}'\n"
                "Please review and take necessary action."
                )

        else:
            print(f"Supplier {seller} has no linked user.")
