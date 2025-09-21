from django.urls import path
from .views import CityListView, IndustryListView, SpecializedEquipmentListView, SupplierProfileDetailView,new_view

app_name = 'setting'
urlpatterns = [
    path('profile-setting/', SupplierProfileDetailView.as_view(), name='supplier-profile-setting'),
    path('userprofile-update/',new_view.as_view(),name="new-setting-page"),

    path('industries/', IndustryListView.as_view(), name='industries-list'),
    path('specialized-equipment/', SpecializedEquipmentListView.as_view(), name='specialized-equipment-list'),
    path('cities/', CityListView.as_view(), name='cities-list'),
]
