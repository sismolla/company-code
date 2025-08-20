from django.contrib import admin
from .models import (
    DosageForm,
    ChatMessage,
    Notification,
    ChatThread,
    Product,
    Supplier,
    Review,
    ReportAbuse,
    UserProducts,
    Order,
    OrderItem,
    SocialMediaPost
)
# Register your models here.

admin.site.register([DosageForm,Supplier,Notification,ChatThread,Product,ChatMessage,Review,ReportAbuse,UserProducts,Order,OrderItem,SocialMediaPost])