from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CityListView, FollowUserView, IndustryListView, SpecializedEquipmentListView, SupplierProfileDetailView, UnfollowUserView, QuoteRequestViewSet, QuotesPageView, QuotesManageView, QuotesListPageView

app_name = 'setting'

router = DefaultRouter()
router.register(r'quotes', QuoteRequestViewSet, basename='quotes')


urlpatterns = [
    path('profile-setting/', SupplierProfileDetailView.as_view(), name='supplier-profile-setting'),

    path('industries/', IndustryListView.as_view(), name='industries-list'),
    path('specialized-equipment/', SpecializedEquipmentListView.as_view(), name='specialized-equipment-list'),
    path('cities/', CityListView.as_view(), name='cities-list'),

    path("follow/", FollowUserView.as_view(), name="follow-user"),
    path("unfollow/<int:pk>/", UnfollowUserView.as_view(), name="unfollow-user"),
    path('quotes-page/', QuotesPageView.as_view(), name='quotes-page'),
    path('manage-quotes/', QuotesManageView.as_view(), name='manage-quotes'),
    path('quotes-list/', QuotesListPageView.as_view(), name='quotes-list'),
    path('api/', include(router.urls)),
]

