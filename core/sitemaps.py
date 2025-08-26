from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Supplier

class StaticViewSitemap(Sitemap):
    def items(self):
        return [
            'landing:landing-page',
            'landing:faq',
            'landing:suppliers-list',
            'about-us',
            'contact-us',
            'privacy-policy',
            'terms-policy',
        ]  # your named URLs

    def location(self, item):
        return reverse(item)

class SupplierSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Supplier.objects.all()

    def location(self, obj):
        return reverse("landing:product-provider-detail", kwargs={"pk": obj.pk})

    def lastmod(self, obj):
        return obj.created_at
