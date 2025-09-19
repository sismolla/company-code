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
    SocialMediaPost,
    Post,
    UniversalNotification,
    City
)
# Register your models here.
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["content", "platform", "approved", "scheduled_time", "posted"]
    list_filter = ["approved", "platform", "posted"]
    actions = ["approve_posts"]

    def approve_posts(self, request, queryset):
        queryset.update(approved=True)

admin.site.register([DosageForm,Supplier,Notification,ChatThread,Product,ChatMessage,Review,ReportAbuse,UserProducts,Order,OrderItem,SocialMediaPost,UniversalNotification,City])