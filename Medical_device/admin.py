from django.contrib import admin
from .models import Category, MedicalDevice, Attribute, ProductAttributeValue, ProductImage

admin.site.register([Category, MedicalDevice, Attribute, ProductAttributeValue,ProductImage])
# Register your models here.
