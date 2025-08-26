from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models import Avg
import uuid
from django.utils import timezone
from datetime import timedelta

class DosageForm(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):

    RESPONSE_TIME_CHOICES = [
        ('instantly', 'Instantly'),
        ('3-5', 'Within 3 to 5 Minutes'),
        ('longer', 'A little longer'),
    ]


    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile', null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=False, null=False)
    whatsapp_link = models.URLField(blank=True, null=True)
    telegram_link = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='supplier_logos/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    response_time = models.CharField(max_length=10, choices=RESPONSE_TIME_CHOICES, default='instantly')
    created_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        from .models import Review  # avoid circular import
        avg = Review.objects.filter(product__supplier=self).aggregate(avg=Avg('rating'))['avg']
        return round(avg, 2) if avg else 0


class Product(models.Model):
    product_id = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    name = models.CharField(max_length=100)
    strength = models.CharField(max_length=50)
    expire_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    dosage_form = models.ForeignKey(DosageForm, on_delete=models.CASCADE, related_name='dosage')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return f"{self.name} ({self.strength})"

User = get_user_model()

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.recipient.username}:"


class ChatThread(models.Model):
    user_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_threads_started')
    user_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_threads_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_1', 'user_2')

    def __str__(self):
        return f"Chat between {self.user_1.username} and {self.user_2.username}"

class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"

class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)  # or use ForeignKey to User if needed
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])  # 1–5 stars
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # newest first

    def __str__(self):
        return f"{self.reviewer_name} - {self.product.name} ({self.rating}★)"
    
class ReportAbuse(models.Model):
    REASON_CHOICES = [
        ('illegal_fraudulent', 'This is illegal/fraudulent'),
        ('spam', 'This product is spam'),
        ('wrong_price', 'The price is wrong'),
        ('wrong_category', 'Wrong category'),
        ('prepayment', 'Seller asked for prepayment'),
        ('sold', 'It is sold'),
        ('unreachable_user', 'User is unreachable'),
        ('counterfeit', 'This product is counterfeit/fake'),
        ('offensive_content', 'Contains offensive or inappropriate content'),
        ('misleading', 'Misleading or false information'),
        ('duplicate', 'Duplicate listing'),
        ('expired', 'Product expired or outdated'),
        ('prohibited_item', 'Prohibited item for sale'),
        ('other', 'Other'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='abuse_reports')
    reporter_email = models.EmailField(blank=False, null=False)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True, help_text='Optional, provide details if reason is "Other"')
    reported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Abuse report on {self.product.name} - {self.get_reason_display()}"


class UserProducts(models.Model):
    description = models.TextField(max_length=2000,null=True,blank=True)
    supplier = models.OneToOneField(Supplier,related_name='user_supplier',on_delete=models.CASCADE)
    bulk_discount_available = models.BooleanField(default=False)
    offer_delivery = models.BooleanField(default=False)



class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_full_name = models.CharField(max_length=50,null=False,blank=False)
    customer_email_address = models.EmailField(null=False,blank=False)
    customer_phone = models.IntegerField(blank=False,null=False)
    customer_pharmacy_name = models.CharField(max_length=200,blank=False,null=False)
    customer_delivery_address = models.CharField(max_length=200,blank=False,null=False)
    expiry_date = models.DateTimeField(null=True, blank=True)
    supplier = models.ForeignKey("Supplier", related_name="orders", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Order {self.id} by {self.customer_full_name}"
    

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def has_expired(self):
        return timezone.now() > self.expiry_date

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", related_name="order_items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class SocialMediaPost(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='telegram_posts')
    products = models.ManyToManyField(Product)
    template_used = models.IntegerField(default=1)
    post_date = models.DateField(auto_now_add=True)
    posted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.supplier.name} - {self.post_date}"


# class SupplierProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)  # group/channel chat_id
#     post_frequency = models.CharField(
#         max_length=20,
#         choices=[
#             ("daily", "Daily"),
#             ("weekly", "Weekly"),
#             ("custom", "Custom"),
#         ],
#         default="daily"
#     )
#     custom_time = models.TimeField(blank=True, null=True)  # if they want exact time posting



class ContactUs(models.Model):
    SUBJECT_CHOICES = [
        ('wholesaler', 'wholesaler'),
        ('buyer', 'buyer'),
        ('partnership', 'partnership'),
        ('support', 'support'),
        ('other','other')
    ]
    name = models.CharField(max_length=50,null=False,blank=False)
    email = models.EmailField(null=False,blank=False)
    subject = models.CharField(choices=SUBJECT_CHOICES, null=False,blank=False,max_length=300)
    message = models.TextField(null=False,blank=False,max_length=2000)