from django.db import models
from core.models import Supplier,City
from Medical_device.models import Category
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.models import Supplier
User = settings.AUTH_USER_MODEL

class Industry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class SupplierProfile(models.Model):
    user = models.OneToOneField(Supplier, on_delete=models.CASCADE)
    industries = models.ManyToManyField(Industry, blank=True)
    specialized_equipment = models.ManyToManyField(Category, blank=True)
    cities = models.ManyToManyField(City, blank=True)


    def __str__(self):
        return f"{self.user.name} Profile"

class UserConnection(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")  # prevent duplicates

    def __str__(self):
        return f"{self.follower} follows {self.following}"

class QuoteRequest(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="quote_requests")
    quote_id = models.CharField(max_length=20, unique=True, editable=False)
    message = models.TextField(max_length=2000)
    attachment = models.FileField(upload_to="quote_attachments/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.quote_id:
            year = timezone.now().year
            last_request = QuoteRequest.objects.filter(
                quote_id__startswith=f"RQ-{year}"
            ).order_by("-id").first()

            last_number = int(last_request.quote_id.split("-")[-1]) if last_request else 0
            self.quote_id = f"RQ-{year}-{last_number + 1:04d}"

        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return timezone.now() < self.expiry_date

    @property
    def status_badge(self):
        return "🟢 Active" if self.is_active else "🔴 Expired"

    def clean(self):
        if self.attachment and self.attachment.size > 5 * 1024 * 1024:
            from django.core.exceptions import ValidationError
            raise ValidationError("Attachment must be less than 5MB.")

    @classmethod
    def cleanup_expired(cls):
        cutoff = timezone.now() - timedelta(days=30)
        expired_quotes = cls.objects.filter(expiry_date__lt=cutoff)
        count = expired_quotes.count()
        expired_quotes.delete()
        return count

    def __str__(self):
        return f"{self.quote_id} - {self.supplier.name}"

class QuoteImage(models.Model):
    quote_request = models.ForeignKey(
        "QuoteRequest", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="quote_images/")

    def clean(self):
        # Validate file size <= 2MB
        if self.image.size > 2 * 1024 * 1024:
            from django.core.exceptions import ValidationError
            raise ValidationError("Each image must be less than 2MB.")

    def __str__(self):
        return f"Image for {self.quote_request.quote_id}"
