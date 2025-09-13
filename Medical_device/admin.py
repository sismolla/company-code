from django.contrib import admin
from .models import Category, MedicalDevice, Attribute, ProductAttributeValue, ProductImage, ImpressionAggregate

admin.site.register([Category, MedicalDevice, Attribute, ProductAttributeValue,ProductImage, ImpressionAggregate])
# Register your models here.
