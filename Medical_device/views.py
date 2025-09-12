
import json
from django.shortcuts import render
from rest_framework.response import Response 
from rest_framework.views import APIView
from .serializer import CategorySerializer, ProductSerializer
from .models import MedicalDevice, Category, ProductAttributeValue, ProductImage
from django.views.generic import TemplateView
from rest_framework import serializers,status,viewsets
from django.views.generic import ListView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.template.loader import render_to_string
from rest_framework.permissions import IsAuthenticated
from core.models import Supplier
from core.models import UserProducts
from django.contrib.auth.mixins import LoginRequiredMixin

class DeviceAddPage(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'device_form.html'

class DeviceViewPage(TemplateView):
    template_name = 'device_view.html'

class CategoryApiView(APIView):
    def get(self, request, *args, **kwargs):
        categories = Category.objects.filter(parent__isnull=True)  # only top-level
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

class DeviceHomePage(TemplateView):
    template_name = 'home_listing.html'

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        attributes = request.data.get("attributes")
        images = request.FILES.getlist("images")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Assign supplier
        user = request.user
        try:
            supplier = Supplier.objects.get(user=user)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError("Supplier not found for this user.")

        product = serializer.save(supplier=supplier)

        if attributes:
            try:
                attributes = json.loads(attributes)
                for attr in attributes:
                    if "attribute_id" not in attr or "value" not in attr:
                        raise serializers.ValidationError("Each attribute must include 'attribute_id' and 'value'")
                    ProductAttributeValue.objects.create(
                        product=product,
                        attribute_id=attr["attribute_id"],
                        value=attr["value"],
                    )
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid attributes format. Must be valid JSON.")

        # Handle images (limit 5)
        if len(images) > 5:
            raise serializers.ValidationError("You can upload up to 5 images only.")
        for img in images:
            ProductImage.objects.create(product=product, image=img)

        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    def get_queryset(self,request=None):
        user = self.request.user
        try:
            supplier = Supplier.objects.get(user=user)
            return MedicalDevice.objects.filter(supplier=supplier)
        except Supplier.DoesNotExist:
            return MedicalDevice.objects.none()
    
    def update(self, request, *args, **kwargs):
        attributes = request.data.get("attributes")
        images = request.FILES.getlist("images")
        brochure = request.FILES.get("brochure")  # optional single file

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # ---- Update attributes ----
        if attributes:
            try:
                attributes = json.loads(attributes) if isinstance(attributes, str) else attributes
                for attr in attributes:
                    attr_id = attr.get("attribute") or attr.get("attribute_id")
                    value = attr.get("value")
                    if attr_id and value is not None:
                        ProductAttributeValue.objects.update_or_create(
                            product=product,
                            attribute_id=attr_id,
                            defaults={"value": value},
                        )
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid attributes format")

        # ---- Handle deleted images ----
        deleted_images = request.data.get("deleted_images")
        if deleted_images:
            try:
                deleted = json.loads(deleted_images) if isinstance(deleted_images, str) else deleted_images
                ProductImage.objects.filter(id__in=deleted, product=product).delete()
            except Exception:
                raise serializers.ValidationError("Invalid deleted_images format")

        # ---- Add new images (respect max 5 images) ----
        if images:
            current_count = product.images.count()
            if current_count + len(images) > 5:
                raise serializers.ValidationError("You can upload up to 5 images only.")
            for img in images:
                ProductImage.objects.create(product=product, image=img)

        # ---- Update brochure (replace if new one is uploaded) ----
        if brochure:
            product.brochure = brochure
            product.save()

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

class ProductListView(ListView):
    model = MedicalDevice
    template_name = 'product_list.html'  
    context_object_name = 'products'  
    paginate_by = 50
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = MedicalDevice.objects.all().select_related('category').prefetch_related('images', 'attributes__attribute')
        
        # Apply filters
        search_query = self.request.GET.get('search')
        category_filter = self.request.GET.get('category')
        manufacturer_filter = self.request.GET.get('manufacturer')
        ordering = self.request.GET.get('ordering', '-created_at')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(intended_use__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
            
        if manufacturer_filter:
            queryset = queryset.filter(manufacturer=manufacturer_filter)
            
        if ordering:
            queryset = queryset.order_by(ordering)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add categories and manufacturers for filters
        context['categories'] = Category.objects.all()
        context['manufacturers'] = MedicalDevice.objects.values_list('manufacturer', flat=True).distinct()
        context['new_arrivals'] = MedicalDevice.objects.all().order_by('-created_at')[:10]
        # Add selected category for display
        category_id = self.request.GET.get('category')
        if category_id:
            try:
                context['selected_category'] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass
                
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return only the partial HTML (product grid + pagination)
            html = render_to_string('product_list_partial.html', context, self.request)
            return HttpResponse(html)  # 🔥 raw HTML, not JSON
        return super().render_to_response(context, **response_kwargs)

class ProductDetailView(DetailView):
    model = MedicalDevice
    template_name = 'product_detail.html'
    context_object_name = 'product'
    
    def get_object(self, queryset=None):
        # Get the product with related data
        return get_object_or_404(
            MedicalDevice.objects.select_related('category')
                          .prefetch_related('images', 'attributes__attribute'),
            id=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related products (same category)
        context['related_products'] = MedicalDevice.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id).select_related('category')[:10]
        context['warranty'] = self.object.warranty
        context['supplier'] = self.object.supplier
        context['user_supplier'] = UserProducts.objects.filter(supplier=self.object.supplier.id).first()
        return context

def supplier_products(request, pk):
    supplier = get_object_or_404(Supplier, id=pk)
    products = supplier.devices.prefetch_related("images", "attributes__attribute", "category")
    
    contact_info = {
        'Phone': supplier.phone if hasattr(supplier, 'phone') else None,
        'Email': supplier.user.email if hasattr(supplier.user, 'email') else None,
        'Whatsapp': supplier.whatsapp_link if hasattr(supplier, 'whatsapp_link') else None,
        'Telegram': supplier.telegram_link if hasattr(supplier, 'telegram_link') else None,
    }

    member_since = supplier.user.date_joined.strftime("%B %Y")  

    # Remove empty values
    contact_info = {k:v for k,v in contact_info.items() if v}

    return render(request, "provider/detail_two.html", {"supplier": supplier, "products": products,'contact_info': contact_info,"member_since": member_since,
})
