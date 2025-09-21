# views.py
from django.shortcuts import render
from rest_framework import generics, permissions

from Medical_device.models import Category
from .models import Industry, SupplierProfile
from .serializers import CitySerializer, IndustrySerializer, SpecializedEquipmentSerializer, SupplierProfileSerializer
from core.models import City, Supplier
from django.views import View
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

class new_view(View):
    template_name = 'settings.html'
    def get(self,request):
        return render(request,self.template_name)
    
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