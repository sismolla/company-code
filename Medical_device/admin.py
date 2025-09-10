from django.contrib import admin
from .models import Category, Product, Attribute, ProductAttributeValue, ProductImage

admin.site.register([Category, Product, Attribute, ProductAttributeValue,ProductImage])
# Register your models here.
