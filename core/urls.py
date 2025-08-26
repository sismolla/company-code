from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import google_calendar_webhook, ChatMessageCreateAPIView, ChatThreadCreateAPIView, ChatThreadListAPIView, ContactUsViewSet, CustomerDashboardView, FAQView, HelpPageView, MarkMessagesAsReadView, MessageView, NotificationApi, Pharmacy_page,ProductApiView,DosageApi, ProductBulkUploadView, ProductDetailAPIView, ProductProvider, ProductProviderDetailPage, ProductViewSet, ProductsView, ProfilePageView, ReportAbuseCreateAPIView, ReviewCreateAPIView,ProductDetailView, SignUpPageView, SupplierOrderDetailPage, SupplierProfileViewSet, SupplierSignupAPIView, UserLoginAPIView, UserOrderDetailUpdateView, UserOrdersListView, UserProfileAPIView, logout_view, ProductProviderListPage,OrderCreateView, SupplierOrderPage


app_name = 'landing'
router = DefaultRouter()
router.register(r'products', ProductViewSet,) # This line is correct
router.register(r'user-models', ProductProvider, basename='user-model')
router.register(r'user-contactus', ContactUsViewSet)

urlpatterns = [
    path('logout/', logout_view, name='logout'),

    # API endpoints handled manually
    path('api/signup/', SupplierSignupAPIView.as_view(), name='supplier-signup'),
    path('api/login/', UserLoginAPIView.as_view(), name='user-login'),
    path('dosage/api/', DosageApi.as_view(), name='dosage'),
    path('reviews/create/', ReviewCreateAPIView.as_view(), name='review-create'),
    path('report-abuse/', ReportAbuseCreateAPIView.as_view(), name='report-abuse-create'),
    path('product/api/',ProductApiView.as_view(),name='products-api-view'),
    # Chat API endpoints 

    path('thread/<int:thread_pk>/mark-as-read/', MarkMessagesAsReadView.as_view(), name='mark-as-read'),
    path('threads/', ChatThreadListAPIView.as_view(), name='chat-thread-list'),
    path('threads/create/', ChatThreadCreateAPIView.as_view(), name='chat-thread-create'),
    path('messages/create/', ChatMessageCreateAPIView.as_view(), name='chat-message-create'),
    path('message/', MessageView.as_view(), name='message-view'),
    path('api/notification/', NotificationApi.as_view(),name='notification-view'),

    # Views for the web pages
    path('user/signup/', SignUpPageView.as_view(), name='user-signup'),
    path('product/detail/<int:pk>/', ProductDetailView.as_view(), name='detail'),
    path('product/api/<int:pk>/',ProductDetailAPIView.as_view(),name='api-product-detail'),
    path('dashboard/', CustomerDashboardView.as_view(), name='dashboard'),
    path('profile/', ProfilePageView.as_view(), name='profile'),
    path('api/profile/', UserProfileAPIView.as_view(),name = 'profile-api'),
    path('help/', HelpPageView.as_view(), name='help'),
    path('user/products/', ProductsView.as_view(), name='user-products'),
    path('', Pharmacy_page.as_view(), name='landing-page'),

    path('list/',ProductProviderListPage.as_view(),name='suppliers-list'),
    path('supplier-detail/<int:pk>/', ProductProviderDetailPage.as_view(), name='product-provider-detail'),
    path('user-models-page/',SupplierProfileViewSet.as_view(),name='single-page-supplier'),

    path('order/creation/',OrderCreateView.as_view(),name='order-creation'),
    path('orders/', UserOrdersListView.as_view(), name='my-orders'),
    path('orders/<uuid:pk>/', UserOrderDetailUpdateView.as_view(), name='order-detail-update'),
    path('orders/view/', SupplierOrderPage.as_view(), name='order-view'),
    path('order/<uuid:pk>/', SupplierOrderDetailPage.as_view(), name='order-detail'),
    path("products/bulk-upload/", ProductBulkUploadView.as_view(), name="product-bulk-upload"),

    path('api/', include(router.urls)),
    path('faq/',FAQView.as_view(),name='faq'),

    path('calendar-webhook/', google_calendar_webhook, name='calendar-webhook'),

]

urlpatterns += router.urls