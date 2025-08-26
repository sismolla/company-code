from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework import generics
from rest_framework.filters import SearchFilter,OrderingFilter
from .models import ChatMessage, ChatThread, ContactUs, DosageForm, Order, Product, ReportAbuse, Review, Supplier, Notification, UserProducts
from .filters import ProductFilter
from .serializers import ChatMessageSerializer, ChatThreadCreateSerializer, ChatThreadSerializer, ContactUsSerializer, DosageFormSerializer, NotificationSerializer, OrderSerializer, ProductDetailSerializer, ProductProviderSerializer, ProductSerializerView, SupplierOrderSerializer, SupplierUpdateSerializer, ReportAbuseSerializer, ReviewSerializer, SupplierSignupSerializer, UserSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.views.generic import TemplateView
from rest_framework import  permissions
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
import openpyxl
from django.core.files.storage import default_storage
from dateutil import parser


def logout_view(request):
    logout(request)  # This clears the session
    return redirect('landing:landing-page')  # Redirect to your login page or home

class Pharmacy_page(View):
    template_name = 'pharmacy.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class ProductDetailView(View):
    template_name = 'detail.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'product': product})
    
# class ProductDetailAPIView(generics.RetrieveAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializerView
#     def get_queryset(self):
#         return Product.objects.select_related("supplier__user_supplier").all()
#
#     def retrieve(self, request, *args, **kwargs):
#         response = super().retrieve(request, *args, **kwargs)
#         product = self.get_object()
#         userproduct = getattr(product.supplier, "user_supplier", None)
#         print('this is the userproduct', userproduct)
#         response.data["userproduct_id"] = userproduct.id if userproduct else None
#         return response

class ProductApiView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializerView
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter

    # Search fields
    search_fields = [
        'name',
        'supplier__name',
        'dosage_form__name'
    ]

    # Allow ordering by these fields
    ordering_fields = ['price', 'stock_quantity', 'name']
    ordering = ['price']  # default order

class DosageApi(generics.ListAPIView):
    queryset = DosageForm.objects.all()
    serializer_class = DosageFormSerializer

class ReviewCreateAPIView(generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def get(self,request):
        message = 'You just got a new review!!'
        user = self.request.user
        Notification.objects.create(recipient=user,
                                    message= message
                                    )

class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer

class ReportAbuseCreateAPIView(generics.CreateAPIView):
    queryset = ReportAbuse.objects.all()
    serializer_class = ReportAbuseSerializer
    permission_classes = [AllowAny]  

class MessageView(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'message.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class CustomerDashboardView(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'dashboard.html'
    context_object_name = 'dashboard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context["dashboard"] = Product.objects.filter(supplier__user=user)[:10]
            # Stats
            context["count_products"] = Product.objects.filter(supplier__user=user).count()
            supplier = Supplier.objects.filter(user=user).first()
            context['reviews'] = supplier.average_rating if supplier else 0
            context['logo'] = supplier.logo if supplier.logo else None
        else:
            context["dashboard"] = []
            context["count_products"] = 0
            context['reviews'] = 0
            context['unread_messages'] = 0

        return context

class ChatThreadCreateAPIView(generics.CreateAPIView):
    serializer_class = ChatThreadCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user_1=self.request.user)

class ChatThreadListAPIView(generics.ListAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['user_1__username', 'user_2__username']

    def get_queryset(self):
        user = self.request.user
        return ChatThread.objects.filter(Q(user_1=user) | Q(user_2=user))

class ChatMessageCreateAPIView(generics.CreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        thread = serializer.validated_data['thread']
        if user != thread.user_1 and user != thread.user_2:
            raise PermissionError("You are not allowed to send messages in this thread.")
        serializer.save(sender=user)
        Notification.objects.create(
            recipient=thread.user_1 if user != thread.user_1 else thread.user_2,
            message= 'You have a new Message',
        ).save()

class MarkMessagesAsReadView(APIView):
    def post(self, request, thread_pk):
        thread = get_object_or_404(ChatThread, pk=thread_pk)
        user = request.user

        if user not in [thread.user_1, thread.user_2]:
            return Response(
                {"detail": "You do not have permission to access this thread."},
                status=status.HTTP_403_FORBIDDEN
            )
        unread_msgs_count = ChatMessage.objects.filter(
            thread=thread,
            is_read=False
        ).exclude(
            sender=user
        ).update(is_read=True)

        return Response(
            {"detail": f"{unread_msgs_count} messages marked as read."},
            status=status.HTTP_200_OK
        )

class ProfilePageView(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'profile.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Supplier.objects.get(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        Notification.objects.create(
            recipient=self.request.user,
            message="Your profile has been updated successfully."
        )
    
class HelpPageView(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'help.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class ProductsView(LoginRequiredMixin,TemplateView):
    login_url = '/user/signup/'
    template_name = 'products.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class SignUpPageView(TemplateView):
    template_name = 'signup/sighup.html'

class SupplierSignupAPIView(generics.CreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSignupSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic  # ensures atomicity
    def perform_create(self, serializer):
        # Save the supplier instance first
        supplier = serializer.save()
        UserProducts.objects.create(supplier=supplier)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return response

class UserLoginAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)  # This sets the session cookie
            return Response({'message': 'Login successful'})
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()

    def get_queryset(self):
        supplier = Supplier.objects.get(user=self.request.user)
        qs = Product.objects.filter(supplier=supplier)
        return qs
    def perform_create(self, serializer):
        supplier = get_object_or_404(Supplier,user=self.request.user)
        serializer.save(supplier=supplier,product_id=uuid.uuid4())

    def get_serializer_context(self):
        context= super().get_serializer_context()
        context['request'] = self.request

        return context

class NotificationApi(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Fetch notifications either for this user OR global notifications (recipient=None)
        qs = Notification.objects.filter(recipient=user.id).order_by('-created_at')
        return qs

    def patch(self, request, *args, **kwargs):
        unread_qs = Notification.objects.filter(recipient=request.user.id, is_read=False)
        unread_qs.update(is_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)

class ProductProvider(viewsets.ModelViewSet):
    queryset = UserProducts.objects.all()
    serializer_class = ProductProviderSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # keep only some fields for list
        data = [
                {
                    "id": item["id"],
                    "supplier": item["supplier"]["name"],
                    "address": item["supplier"]["address"],
                    "description": item["description"],
                    "average_rating": [p['average_rating'] for p in item['products']],  # still list per product
                    "logo": item["supplier"]["logo"],  # ✅ single supplier logo
                }

            for item in serializer.data
        ]
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)  # full detail


    def perform_create(self, serializer):
        """
        Automatically associate the supplier based on the logged-in user.
        """
        # assuming user has a supplier profile
        supplier = self.request.user.supplier_profile
        serializer.save(supplier=supplier)

class ProductProviderListPage(TemplateView):
    template_name = 'provider/list.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)
 
class ProductProviderDetailPage(View):
    template_name = 'provider/detail.html'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        supplier = Supplier.objects.filter(user=request.user.id).first()
        return render(request, self.template_name, {
            'product': product,
            'supplier': product.supplier,
            "logo": supplier.logo if supplier and supplier.logo else None,

        })

class SupplierProfileViewSet(generics.RetrieveUpdateAPIView):
    serializer_class = SupplierUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]  # only logged-in users

    def get_object(self):
        # Get or create the UserProducts instance for the current supplier
        supplier = get_object_or_404(Supplier, user=self.request.user)
        obj, created = UserProducts.objects.get_or_create(supplier=supplier)
        return obj

class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        first_item = order.items.first()
        supplier = first_item.product.supplier  
        supplier_user = supplier.user

        # Send notification
        Notification.objects.create(
            recipient=supplier_user,
            message=f"You have a new order from {order.customer_full_name}."
        )

        return Response(
            {
                "message": "Order created successfully",
                "order_id": order.id,
            },
            status=status.HTTP_201_CREATED,
        )

class UserOrdersListView(generics.ListAPIView):
    serializer_class = SupplierOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(supplier=self.request.user.id,is_active=True)
    
class UserOrderDetailUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = SupplierOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(supplier=self.request.user.id)
    
class SupplierOrderPage(LoginRequiredMixin, TemplateView):
    login_url = '/user/signup/'
    template_name = 'provider/orders.html'

class SupplierOrderDetailPage(LoginRequiredMixin,View):
    login_url = '/user/signup/'
    template_name = 'provider/order_detail.html'
    
    def get(self, request, pk):
        # Fetch the order, not the product
        order = get_object_or_404(Order, pk=pk, supplier=request.user.id)
        return render(request, self.template_name, {'order': order})
    
class ProductBulkUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    FIELD_ALIASES = {
        "name": ["name", "product name", "product_name"],
        "strength": ["strength", "dose"],
        "expire_date": ["expire_date", "expiry", "expire date", "expiry date", "expiration date"],
        "price": ["price", "cost", "unit price"],
        "stock_quantity": ["stock_quantity", "stock quantity", "quantity", "stock", "stock qty"],
        "dosage_form_id": ["dosage_form_id", "dosage", "dosage form", "form"],
    }

    def normalize_headers(self, headers):
        normalized = {}
        for h in headers:
            if not h:
                continue
            h_lower = str(h).strip().lower()
            for field, aliases in self.FIELD_ALIASES.items():
                if h_lower in [a.lower() for a in aliases]:
                    normalized[h] = field
                    break
        return normalized

    def resolve_dosage_form(self, value):
        if not value:
            return None
        value = str(value).strip()
        try:
            return DosageForm.objects.get(name__iexact=value)  # return object
        except DosageForm.DoesNotExist:
            return None

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        file_path = default_storage.save("tmp/products.xlsx", excel_file)
        abs_path = default_storage.path(file_path)

        created_count = 0
        updated_count = 0
        errors = []

        try:
            wb = openpyxl.load_workbook(abs_path)
            sheet = wb.active
            supplier = get_object_or_404(Supplier, user=request.user)

            headers = [cell.value for cell in sheet[1]]
            header_map = self.normalize_headers(headers)

            for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    raw_row = dict(zip(headers, row))
                    row_data = {header_map.get(k): v for k, v in raw_row.items() if header_map.get(k)}

                    # Validate required fields (None or empty string is missing)
                    missing = [f for f in ["name", "strength", "price", "stock_quantity", "dosage_form_id"]
                               if row_data.get(f) in [None, ""]]
                    if missing:
                        errors.append(f"Row {i}: Missing required fields: {', '.join(missing)}")
                        continue

                    dosage_form = self.resolve_dosage_form(row_data["dosage_form_id"])
                    if not dosage_form:
                        errors.append(f"Row {i}: Invalid dosage form '{row_data['dosage_form_id']}'")
                        continue

                    # Parse expire_date
                    expire_date = None
                    if row_data.get("expire_date"):
                        try:
                            expire_date = parser.parse(str(row_data["expire_date"])).date()
                        except Exception:
                            errors.append(f"Row {i}: Invalid date format '{row_data['expire_date']}'")
                            continue

                    # Try update first
                    product = Product.objects.filter(
                        name=str(row_data.get("name")).strip(),
                        strength=str(row_data.get("strength")).strip(),
                        dosage_form=dosage_form,
                        supplier=supplier,
                    ).first()

                    if product:
                        product.stock_quantity = row_data.get("stock_quantity")
                        product.price = row_data.get("price")
                        product.expire_date = expire_date
                        product.save()
                        updated_count += 1
                    else:
                        Product.objects.create(
                            product_id=str(uuid.uuid4()),
                            name=str(row_data.get("name")).strip(),
                            strength=str(row_data.get("strength")).strip(),
                            expire_date=expire_date,
                            price=row_data.get("price"),
                            stock_quantity=row_data.get("stock_quantity"),
                            dosage_form=dosage_form,
                            supplier=supplier,
                        )
                        created_count += 1

                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")

        finally:
            default_storage.delete(file_path)

        return Response(
            {
                "message": f"Imported {created_count} new products, Updated {updated_count} existing products",
                "errors": errors,
            },
            status=status.HTTP_201_CREATED,
        )
    
class ContactUsViewSet(viewsets.ModelViewSet):
    queryset = ContactUs.objects.all()
    serializer_class = ContactUsSerializer
    http_method_names = ['post']


class FAQView(TemplateView):
    template_name = 'faq.html'

    def get(self,request):
        if request.user.is_authenticated:
            supplier = get_object_or_404(Supplier,user=self.request.user)
            context = {
            'logo' : supplier.logo
            }

            return render(request,self.template_name,context)
        return render(request,self.template_name)


def handler404(request, exception):
    return render(request, '404.html', status=404)


def robots_txt(request):
    content = """
    User-agent: *
    Disallow: /admin/
    Allow: /
    Sitemap: http://127.0.0.1:8000/sitemap.xml
    """
    return HttpResponse(content, content_type="text/plain")


# views.py
from django.http import HttpResponse
import json
from .tasks import post_next_supplier_products

def google_calendar_webhook(request):
    # Call your function here
    post_next_supplier_products()
    return HttpResponse("Task executed successfully", status=200)



