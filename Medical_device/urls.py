from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CategoryApiView, ProductDetailView, ProductListView,ProductViewSet, DeviceAddPage, DeviceViewPage, DeviceHomePage
from rest_framework.routers import DefaultRouter



app_name = 'medical_device'

urlpatterns = [
    path('add/device/',DeviceAddPage.as_view(),name='add-device'),
    path('view/device/',DeviceViewPage.as_view(),name='view-device'),
    path('list/device/', ProductListView.as_view(), name='product_list'),
    path('list/device/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('medical_device_upload_api/', CategoryApiView.as_view(), name='medical-device-upload-api'),
    path('home/device/', DeviceHomePage.as_view(), name='device-home'),
]



router = DefaultRouter()
router.register(r"devices", ProductViewSet, basename="product")

urlpatterns += router.urls
