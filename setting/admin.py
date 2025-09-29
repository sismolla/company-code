from django.contrib import admin
from .models import Industry,SupplierProfile,UserConnection, QuoteImage, QuoteRequest
# Register your models here.

admin.site.register([Industry,SupplierProfile,UserConnection, QuoteImage, QuoteRequest])