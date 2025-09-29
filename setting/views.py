# views.py
from django.shortcuts import get_object_or_404, render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from Medical_device.models import Category
from .models import Industry, QuoteRequest, SupplierProfile
from .serializers import CitySerializer, IndustrySerializer, QuoteRequestSerializer, SpecializedEquipmentSerializer, SupplierProfileSerializer
from core.models import City, Notification, Supplier
from django.views import View
from django.conf import settings
from .models import UserConnection
from .serializers import UserConnectionSerializer
from rest_framework import viewsets
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
User = settings.AUTH_USER_MODEL


class SupplierProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the logged-in supplier's profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SupplierProfileSerializer

    def get_object(self):
        # Get the Supplier linked to the current user
        try:
            supplier = Supplier.objects.get(user=self.request.user)
        except Supplier.DoesNotExist:
            raise SupplierProfile.DoesNotExist("Supplier not found for the current user.")

        # Get or create the profile
        profile, created = SupplierProfile.objects.get_or_create(user=supplier)
        return profile

    
class IndustryListView(generics.ListAPIView):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    permission_classes = [permissions.IsAuthenticated]

class SpecializedEquipmentListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = SpecializedEquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class CityListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticated]



class FollowUserView(generics.CreateAPIView):
    serializer_class = UserConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        connection = serializer.save()

        # Send notification to the followed user
        Notification.objects.create(
            recipient=connection.following,
            message=f"{self.request.user.username} has started following you."
        )



class UnfollowUserView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        following_id = kwargs.get("pk")
        connection = get_object_or_404(UserConnection, follower=request.user, following_id=following_id)
        connection.delete()
        return Response({"detail": "Unfollowed successfully."}, status=status.HTTP_204_NO_CONTENT)

class QuoteRequestViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "supplier_profile"):
            return QuoteRequest.objects.filter(supplier=user.supplier_profile).order_by("-created_at")
        return QuoteRequest.objects.none()

    def perform_create(self, serializer):
        supplier = self.request.user.supplier_profile
        serializer.save(supplier=supplier)

class QuotesPageView(LoginRequiredMixin, View):
    login_url = '/user/signup/'
    template_name = 'qoutes_form.html'
    def get(self,request):
        return render(request,self.template_name)

class QuotesManageView(LoginRequiredMixin, View):
    login_url = '/user/signup/'
    template_name = 'manage_quote.html'
    def get(self,request):
        return render(request,self.template_name)
    
class QuotesListPageView(View):
    template_name = 'quotes_list.html'

    def get(self, request):
        # Fetch only active (non-expired) quotes for the current user's supplier profile
        quotes = QuoteRequest.objects.filter(
            expiry_date__gt=timezone.now()
        ).prefetch_related('images').select_related('supplier').order_by('-created_at')
        
        # Calculate stats
        total_quotes = quotes.count()
        active_quotes = total_quotes  # All quotes are active since we filtered
        
        context = {
            'quotes': quotes,
            'total_quotes': total_quotes,
            'active_quotes': active_quotes,
        }
        return render(request, self.template_name, context)