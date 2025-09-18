from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CategoryApiView, ProductDetailView, ProductListView,ProductViewSet, DeviceAddPage, DeviceViewPage, DeviceHomePage, supplier_products, SupplierListPage
from rest_framework.routers import DefaultRouter



app_name = 'medical_device'

urlpatterns = [
    path('add/device/',DeviceAddPage.as_view(),name='add-device'),
    path('view/device/',DeviceViewPage.as_view(),name='view-device'),
    path('list/device/', ProductListView.as_view(), name='product_list'),
    path('list/device/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('medical_device_upload_api/', CategoryApiView.as_view(), name='medical-device-upload-api'),
    path('home/device/', DeviceHomePage.as_view(), name='device-home'),
    path('supplier/products/<int:pk>', supplier_products, name='supplier-products'),

    #providers

    path('device-supplier/list/',SupplierListPage.as_view(),name="device-supplier-list"),
]



router = DefaultRouter()
router.register(r"devices", ProductViewSet, basename="product")

urlpatterns += router.urls
