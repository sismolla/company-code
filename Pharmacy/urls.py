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
from django.contrib.auth import views as auth_views

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

    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/reset/done/'
         ), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),



]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)