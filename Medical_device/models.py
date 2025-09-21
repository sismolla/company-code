from django.db import models
from core.models import Supplier
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ImpressionAggregate(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    impression_count = models.BigIntegerField(default=0)
    click_count = models.BigIntegerField(default=0)
    telegram_views = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("content_type", "object_id")



class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="subcategories"
    )

    def __str__(self):
        return self.name


class MedicalDevice(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    brand = models.CharField(max_length=255, blank=True, null=True)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    intended_use = models.TextField(blank=True, null=True)
    description = models.TextField(max_length= 2000, blank=True, null=True)
    certifications = models.CharField(max_length=255, blank=True, null=True)  # e.g., "FDA, CE"
    brochure = models.FileField(upload_to="products/brochures/", blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    warranty = models.CharField(max_length=255, blank=True, null=True)  # e.g., "2 years"
    created_at = models.DateTimeField(auto_now_add=True)
    impressions = GenericRelation(ImpressionAggregate)
    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey("MedicalDevice", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/images/")

    def __str__(self):
        return f"{self.product.name} - Image"

class Attribute(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField(max_length=100)  
    field_type = models.CharField(
        max_length=50,
        choices=[
            ("text", "Text"),
            ("number", "Number"),
            ("select", "Select"),
        ]
    )
    options = models.TextField(blank=True, null=True, help_text="Comma separated if select")  

    def __str__(self):
        return f"{self.name} ({self.category.name})"

class ProductAttributeValue(models.Model):
    product = models.ForeignKey(MedicalDevice, on_delete=models.CASCADE, related_name="attributes")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"





##the medical device provider list page 








