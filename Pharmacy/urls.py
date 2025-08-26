"""
URL configuration for Pharmacy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.conf.urls import handler404

handler404 = 'core.views.handler404'

from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap, SupplierSitemap
from core.views import robots_txt
sitemaps = {
    'static': StaticViewSitemap,
    'detail':SupplierSitemap
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('core.urls')),
    path('contactus/',TemplateView.as_view(template_name='contact_us.html'),name='contact-us'),
    path('aboutus/',TemplateView.as_view(template_name='aboutus.html'),name='about-us'),
    path('', include('pwa.urls')),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy-policy'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms-policy'),

    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)