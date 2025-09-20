from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.list import ListView
from rest_framework.permissions import AllowAny
from rest_framework import generics
from rest_framework.filters import SearchFilter
from .models import ChatMessage, ChatThread, ContactUs, DosageForm, Order, Product, ReportAbuse, Review, Supplier, Notification, UserProducts, City
from .filters import ProductFilter
from .serializers import ChatMessageSerializer, ChatThreadCreateSerializer, ChatThreadSerializer, ContactUsSerializer, DosageFormSerializer, NotificationSerializer, OrderSerializer, ProductDetailSerializer, ProductProviderSerializer, SupplierOrderSerializer, SupplierUpdateSerializer, ReportAbuseSerializer, ReviewSerializer, SupplierSignupSerializer, UserSerializer
from django.views.generic import TemplateView
from rest_framework import  permissions
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, F, Case, When
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
import uuid
from django.db import models
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
import openpyxl
from django.core.files.storage import default_storage
from dateutil import parser
from .utils import send_order_email,notify_user, send_presentation_email
from rest_framework.pagination import PageNumberPagination
from Medical_device.models import MedicalDevice, ImpressionAggregate
from django.contrib.contenttypes.models import ContentType
import logging
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)
def dosage_forms_map(request):
    # Get all dosage forms ordered by ID (or any field you want)
    dosage_forms = DosageForm.objects.all().order_by('id')  # or use a specific ordering field
    data = {df.name: df.id for df in dosage_forms}
    return JsonResponse(data)


def logout_view(request):
    logout(request)  # This clears the session
    return redirect('landing:landing-page')  # Redirect to your login page or home



class Pharmacy_page(ListView):
    model = Product
    template_name = "pharmacy.html"
    context_object_name = "products"
    paginate_by = 50

    # High-level categories mapping to all 42 dosage forms
    CATEGORY_MAP = {
        "Oral": [
            "Tablet", "Capsule", "Syrup", "Suspension", "Chewable Tablet",
            "Effervescent Tablet", "Dispersible Tablet", "Extended/Controlled Release Tablet",
            "Granules", "Lozenge", "Sachet", "Mouthwash"
        ],
        "Injectable": [
            "Injection", "Powder for Injection", "Ampoule", "Vial", "Infusion Solution"
        ],
        "Topical": [
            "Cream", "Ointment", "Gel", "Lotion", "Patch",
            "Shampoo (Medicated)", "Dental Paste"
        ],
        "Respiratory": [
            "Inhaler", "Nebulizer Solution", "Spray", "Nasal Spray"
        ],
        "Ophthalmic/Otic/Nasal": [
            "Eye Drops", "Eye Ointment", "Ear Drops", "Nasal Drops"
        ],
        "Rectal/Vaginal": [
            "Suppository", "Enema", "Vaginal Tablet", "Vaginal Cream"
        ],
        "Specialized": [
            "Buccal Film/Tablet", "Sublingual Tablet", "Implant"
        ]
    }

    def get_queryset(self):
        queryset = Product.objects.all().select_related("dosage_form", "supplier")
        queryset = queryset.annotate(impression_count=F("impressions__impression_count"))

        # Category filter
        category = self.request.GET.get("category")
        dosage_form = self.request.GET.get("dosage_form")

        if category and category in self.CATEGORY_MAP:
            allowed_forms = DosageForm.objects.filter(name__in=self.CATEGORY_MAP[category])
            queryset = queryset.filter(dosage_form__in=allowed_forms)

            # ✅ Reset dosage_form if it's not in the allowed set
            if dosage_form and not allowed_forms.filter(id=dosage_form).exists():
                dosage_form = None

        if dosage_form:
            queryset = queryset.filter(dosage_form_id=dosage_form)

        


        # Price filter
        min_price = self.request.GET.get("price__gte")
        max_price = self.request.GET.get("price__lte")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(supplier__name__icontains=search) |
                Q(dosage_form__name__icontains=search)
            )

        # Ordering
        ordering = self.request.GET.get("ordering")
        allowed_ordering = ["price", "stock_quantity", "name", "-price", "-stock_quantity", "-name"]
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-impression_count')

        return queryset.annotate(avg_rating=Avg("reviews__rating"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Pass categories with their dosage forms
        categories = []
        for cat_name, forms in self.CATEGORY_MAP.items():
            categories.append({
                "id": cat_name,
                "name": cat_name,
                "dosage_forms": DosageForm.objects.filter(name__in=forms).order_by(
                    Case(*[When(name=f, then=i) for i, f in enumerate(forms)])
                )
            })
        context["categories"] = categories

        # Selected category for frontend
        selected_category_name = self.request.GET.get("category")
        context["selected_category"] = next((c for c in categories if c["id"] == selected_category_name), None)
        context["filters"] = self.request.GET

        return context

    def render_to_response(self, context, **response_kwargs):
        # AJAX response with products partial
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string('products_list_partial.html', context, request=self.request)
            return JsonResponse({'html': html})
        return super().render_to_response(context, **response_kwargs)

from django.views.generic import DetailView

class ProductDetailView(DetailView):
    model = Product
    template_name = 'detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.object.supplier
        member_since = (
            supplier.user.date_joined.strftime("%B %Y") 
            if getattr(supplier, "user", None) else "N/A"
        )
        context['member_since'] = member_since
        return context
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        ct = ContentType.objects.get_for_model(obj)
        agg, _ = ImpressionAggregate.objects.get_or_create(content_type=ct, object_id=obj.pk)
        ImpressionAggregate.objects.filter(pk=agg.pk).update(impression_count=F("impression_count") + 1)

        return obj
    
    
# class ProductApiView(generics.ListAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializerView
#     filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
#     filterset_class = ProductFilter
#     pagination_class = PageNumberPagination
    
#     search_fields = [
#         'name',
#         'supplier__name',
#         'dosage_form__name'
#     ]

#     ordering_fields = ['price', 'stock_quantity', 'name']
#     ordering = ['price']  # default order

class DosageApi(generics.ListAPIView):
    queryset = DosageForm.objects.all()
    serializer_class = DosageFormSerializer
    pagination_class = None

class ReviewCreateAPIView(generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def perform_create(self, serializer):
        review = serializer.save()

        # Get the product's supplier
        product_supplier = review.product.supplier  

        # Customize the notification message
        message = (
            f"🎉 New Review Alert! \n\n"
            f"Product: {review.product.name}\n"
            f"Reviewer: {review.reviewer_name}\n"
            f"Rating: {review.rating}⭐\n"
            f"Comment: {review.comment}"
        )

        # Create notification for the supplier
        Notification.objects.create(
            recipient=product_supplier.user,  # Assuming Supplier model has a OneToOneField to User
            message=message
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
            context['device_products'] = MedicalDevice.objects.filter(supplier=user.id).count()
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
            message= 'You have a new Message from {}'.format(thread.user_1.username if user != thread.user_2 else thread.user_2.username),
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
    template_name = 'signup/sighup.html'  # fix typo if needed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass all cities to the template
        context['cities'] = City.objects.all().order_by('name')
        return context

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
    def get_success_url(self):
        # 1. Respect `next` parameter if it exists
        next_url = self.get_redirect_url()
        print('this is the next url', next_url)
        if next_url:
            return next_url
        # 2. Otherwise go to messages page
        return reverse_lazy("landing:message-view")
    
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
    pagination_class = PageNumberPagination
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # keep only some fields for list
        data = [
            {
                "id": item["id"],
                "supplier": item["supplier"]["name"],
                "phone": item["supplier"]["phone"],
                "email": item["supplier"]["email"],
                "address": item["supplier"]["address"],
                "city":item['supplier']['city'],
                "description": item["description"],
                "average_rating": [p["average_rating"] for p in item["products"]],
                "logo": item["supplier"]["logo"],  # ✅ single supplier logo
            }
            for item in serializer.data if item.get("products") or item.get("medical_devices")   # ✅ only include if products exist
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
        user_product = get_object_or_404(UserProducts, pk=pk)
        supplier = user_product.supplier
        user_profile = UserProducts.objects.filter(supplier=supplier).first()

        # Get all products from this supplier
        products = supplier.products.all()  # QuerySet of Product
        return render(request, self.template_name, {
            'products': products,     # pass all products
            'supplier': supplier,  
            'user_profile':user_profile,   # pass user profile instance
            'logo': supplier.logo if supplier and supplier.logo else None,
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
        send_order_email(order)

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
    
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        old_status = order.status

        try:
            with transaction.atomic():
                # Perform the update
                response = super().update(request, *args, **kwargs)

                # Refresh to get new status
                order.refresh_from_db()
                new_status = order.status

                # Send email only if status changed
                if old_status != new_status:
                    notify_user(order, new_status)

        except Exception as e:
            # Rollback happens automatically if an exception occurs
            return Response(
                {"detail": f"Could not update order: {str(e)}"},
                status=400
            )

        return response
    
class SupplierOrderPage(LoginRequiredMixin, TemplateView):
    login_url = '/user/signup/'
    template_name = 'provider/orders.html'

    def get(self, request):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
        }
        return render(request, self.template_name, context)

class SupplierOrderDetailPage(LoginRequiredMixin,View):
    login_url = '/user/signup/'
    template_name = 'provider/order_detail.html'
    
    def get(self, request, pk):
        supplier = Supplier.objects.filter(user=request.user.id).first()
        order = get_object_or_404(Order, pk=pk, supplier=request.user.id)

        context = {
            "logo": supplier.logo if supplier and supplier.logo else None,
            'order': order
        }

        return render(request, self.template_name, context)


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
        """
        Flexible dosage form matching:
        - Exact match first
        - Then search by keywords (all words must be present)
        - Then search by partial word match
        Returns DosageForm object or None
        """
        if not value:
            return None
        value = str(value).strip().lower()

        # Exact match
        try:
            return DosageForm.objects.get(name__iexact=value)
        except DosageForm.DoesNotExist:
            pass

        # Split words for keyword search
        words = value.split()
        candidates = DosageForm.objects.all()
        matched = []

        # All-words keyword match
        for form in candidates:
            form_name_lower = form.name.lower()
            if all(word in form_name_lower for word in words):
                matched.append(form)

        # Partial word match fallback
        if not matched:
            for form in candidates:
                form_name_lower = form.name.lower()
                if any(word in form_name_lower for word in words):
                    matched.append(form)

        # Handle multiple matches
        if matched:
            matched.sort(key=lambda x: len(x.name), reverse=True)  # longest name first
            if len(matched) > 1:
                logger.warning(
                    f"Ambiguous dosage form match for '{value}': {[m.name for m in matched]}"
                )
            return matched[0]

        # No match
        logger.warning(f"Could not resolve dosage form '{value}'")
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
            wb = openpyxl.load_workbook(abs_path, data_only=True)
            sheet = wb.active
            supplier = get_object_or_404(Supplier, user=request.user)

            headers = [cell.value for cell in sheet[1]]
            header_map = self.normalize_headers(headers)

            for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    raw_row = dict(zip(headers, row))
                    row_data = {header_map.get(k): v for k, v in raw_row.items() if header_map.get(k)}

                    # Validate required fields
                    missing = [f for f in ["name", "strength", "price", "stock_quantity", "dosage_form_id"]
                               if row_data.get(f) in [None, ""]]
                    if missing:
                        errors.append(f"Row {i}: Missing required fields: {', '.join(missing)}")
                        continue

                    dosage_form = self.resolve_dosage_form(row_data["dosage_form_id"])
                    if not dosage_form:
                        errors.append(f"Row {i}: Invalid or unresolvable dosage form '{row_data['dosage_form_id']}'")
                        continue

                    # Parse expire_date safely
                    expire_date = None
                    if row_data.get("expire_date"):
                        try:
                            expire_date = parser.parse(str(row_data["expire_date"])).date()
                        except Exception:
                            errors.append(f"Row {i}: Invalid date format '{row_data['expire_date']}'")
                            continue

                    # Try updating existing product
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
                    errors.append(f"Row {i}: Unexpected error: {str(e)}")
                    logger.exception(f"Error processing row {i}")

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

def handler500(request):
    return render(request, '500.html', status=404)


def robots_txt(request):
    content = """
    User-agent: *
    Disallow: /admin/
    Allow: /
    Sitemap: http://pharmagebeya.com/sitemap.xml
    """
    return HttpResponse(content, content_type="text/plain")


from django.http import HttpResponse
from .tasks import post_next_supplier_products,post_next_supplier_devices

def google_calendar_webhook(request):
    post_next_supplier_products()
    return HttpResponse("Task executed successfully", status=200)

def google_calendar_devices(request):
    post_next_supplier_devices()
    return HttpResponse("Task executed successfully", status=200)


def send_test(request):
    pharma_companies = {
        "Caroga Pharma Ethiopia PLC": [
            "abenetdenberu@gmail.com"
        ],
        "Droga Pharma PLC": [
            "info@drogapharma.com",
            "pharmadroga@gmail.com"
        ],
        "Julphar Ethiopia": [
            "kedir.sherif@julphar.net",
            "eyob.getachew@julphar.net",
            "ahmed.abshiru@julphar.net",
            "eyerusalem.hailemariam@julphar.net",
            "Wibijig.Teshome@julphar.net"
        ],
        "Evan General Trading": [
            "evantrading1@gmail.com"
        ],
        "EPSA (Ethiopian Pharmaceuticals Supply Agency)": [
            "info@epsa.gov.et"
        ],
        "Ethiopian Pharmaceutical Manufacturing S.C.": [
            "epharm@gmail.com"
        ],
        "Dagem Dereje": [
            "dagimderegeimportexport@gmail.com"
        ],
        "Meruna Import & Export": [
            "meruna@ethionet.et",
            "meruna.drugreg@gmail.com",
            "merunaplc@gmail.com"
        ],
        "Hosam Pharma": [
            "info@hosampharma.com"
        ],
        "BGT-Pharma Pharmaceuticals": [
            "bgtpharma@gmail.com"
        ],
        "West Pharma": [
            "westpharma@rocketmail.com"
        ],
        "ZAF Pharmaceuticals": [
            "zafpharmaceuticals@gmail.com",
            "zafg@zafpharma.com"
        ],
        "Beker Pharma": [
            "beker2@bekerpharma.com",
            "ibrahim_nebil@bekerplc.com"
        ],
        "Mesroy International PLC": [
            "mesroy@mesroy.com"
        ],
        "R G and Partners PLC": [
            "rgandpartners@yahoo.com",
            "info@rgandpartners.com"
        ],
        "Agmas Medical": [
            "info@agmasmedical.com"
        ],
        "Elsmed Ethiopia": [
            "dawit.hailu@elsmed-eth.com"
        ],
        "Yohai International": [
            "elhamr@yohainternational.com",
            "yonathanh@yohainternational.com"
        ],
        "Abadir Enterprise": [
            "abadir@ethionet.et"
        ],
        "Behare-Pharma": [
            "beharepharma@ethionet.et"
        ],
        "Beker": [
            "beker@ethionet.et"
        ],
        "Biomed": [
            "biomed@ethionet.et"
        ],
        "Blue German": [
            "bluegerman@ethionet.et"
        ],
        "Caroga Pharma": [
            "carogapharma@ethionet.et"
        ],
        "CBS": [
            "cbs@ethionet.et"
        ],
        "Citrus International Trading PLC": [
            "citrus@ethionet.et"
        ],
        "Conel": [
            "conel@ethionet.et"
        ],
        "Damtit Pharma Trading": [
            "damtit@ethionet.et"
        ],
        "Dat International Trading": [
            "dat@ethionet.et"
        ],
        "Delta Medical": [
            "delta@ethionet.et"
        ],
        "Diverse Electro Medical": [
            "diverse@ethionet.et"
        ],
        "Dream Pharmaceuticals": [
            "dream@ethionet.et"
        ],
        "DS": [
            "ds@ethionet.et"
        ],
        "EBG": [
            "ebg@ethionet.et"
        ],
        "Ekonian": [
            "ekonian@ethionet.et"
        ],
        "Etab International": [
            "etab@ethionet.et"
        ],
        "Ethio Kaz Enterprise": [
            "ethiokaz@ethionet.et"
        ],
        "Etmedix": [
            "etmedix@ethionet.et"
        ],
        "Excellence": [
            "excellence@ethionet.et"
        ],
        "Eyasu Drug": [
            "eyasu@ethionet.et"
        ],
        "Falidco": [
            "falidco@ethionet.et"
        ],
        "Fasih Pharmaceutical": [
            "fasih@ethionet.et"
        ],
        "Gama Pharmaceuticals": [
            "gama@ethionet.et"
        ],
        "Gambi": [
            "gambi@ethionet.et"
        ],
        "GASF-Bio Pharma": [
            "gasfbio@ethionet.et"
        ],
        "GCT": [
            "gct@ethionet.et"
        ],
        "Getmaz": [
            "getmaz@ethionet.et"
        ],
        "Global": [
            "global@ethionet.et"
        ],
        "Gonafer and Sons": [
            "gonafer@ethionet.et"
        ],
        "Grace Trading": [
            "grace@ethionet.et"
        ],
        "Gurmush": [
            "gurmush@ethionet.et"
        ],
        "Habib": [
            "habib@ethionet.et"
        ],
        "Haimet": [
            "haimet@ethionet.et"
        ],
        "Hosam Pharmaceuticals Trading": [
            "hosam@ethionet.et"
        ],
        "Hule Trading": [
            "hule@ethionet.et"
        ],
        "Hyder": [
            "hyder@ethionet.et"
        ],
        "JJ Laboglass Enterprise": [
            "jjlaboglass@ethionet.et"
        ],
        "Jodave": [
            "jodave@ethionet.et"
        ],
        "JOS Hanson and Sons": [
            "joshanson@ethionet.et"
        ],
        "K.M.S.E.G.G.A": [
            "kmsegga@ethionet.et"
        ],
        "Kalwin Multi Supply": [
            "kalwin@ethionet.et"
        ],
        "Kefyalew": [
            "kefyalew@ethionet.et"
        ],
        "Labora International Trading": [
            "labora@ethionet.et"
        ],
        "Lebsi Medical Trading": [
            "lebsi@ethionet.et"
        ],
        "Leyet": [
            "leyet@ethionet.et"
        ],
        "Ma'edot": [
            "maedot@ethionet.et"
        ],
        "Mawenten": [
            "mawenten@ethionet.et"
        ],
        "Medica Pharma": [
            "medica@ethionet.et"
        ],
        "Medicine Net": [
            "medicinet@ethionet.et"
        ],
        "Medite": [
            "medite@ethionet.et"
        ],
        "Meditech Ethiopia": [
            "meditech@ethionet.et"
        ],
        "Menona Medical Supplies": [
            "menona@ethionet.et"
        ],
        "Mesroy": [
            "mesroy@ethionet.et"
        ],
        "MF Pharmaceuticals": [
            "mfpharma@ethionet.et"
        ],
        "Mickel Business Group": [
            "mickel@ethionet.et"
        ],
        "Micro Pharma": [
            "micropharma@ethionet.et"
        ],
        "Mierab": [
            "mierab@ethionet.et"
        ],
        "Mulu Electronics Engineering": [
            "mulu@ethionet.et"
        ],
        "Mulu Tibeb": [
            "mulu@ethionet.et"
        ],
        "Mulunesh": [
            "mulunesh@ethionet.et"
        ],
        "Nared": [
            "nared@ethionet.et"
        ],
        "Nazrawi": [
            "nazrawi@ethionet.et"
        ],
        "Nejat": [
            "nejat@ethionet.et"
        ],
        "Nemo Pharma": [
            "nemo@ethionet.et"
        ],
        "Nesiya": [
            "nesiya@ethionet.et"
        ],
        "Novel Pharmaceuticals": [
            "novel@ethionet.et"
        ],
        "P.T.L": [
            "ptl@ethionet.et"
        ],
        "Petram PLC": [
            "petram@ethionet.et"
        ],
        "PFSA": [
            "pfsa@ethionet.et"
        ],
        "Pharma Birbir PLC": [
            "pharmabirbir@ethionet.et"
        ],
        "Pharma Dessie": [
            "pharmadessie@ethionet.et"
        ],
        "Pharma Lab": [
            "pharmalab@ethionet.et"
        ],
        "Pharma Share Company": [
            "pharmashare@ethionet.et"
        ],
        "Pharma Success": [
            "pharmasuccess@ethionet.et"
        ],
        "Pharma Union": [
            "pharmaunion@ethionet.et"
        ],
        "Pharmaline Pharmaceuticals": [
            "pharmaline@ethionet.et"
        ],
        "Pharma-Tech": [
            "pharmatech@ethionet.et"
        ],
        "PVS Pharmaceuticals": [
            "pvspharma@ethionet.et"
        ],
        "Ramada": [
            "ramada@ethionet.et"
        ],
        "Rangvet PLC": [
            "rangvet@ethionet.et"
        ],
        "Rehobot": [
            "rehobot@ethionet.et"
        ],
        "RG and Partners": [
            "rgandpartners@ethionet.et"
        ],
        "Robdan": [
            "robdan@ethionet.et"
        ],
        "Ruhama Pharmaceutical": [
            "ruhama@ethionet.et"
        ],
        "Sami Addis": [
            "samiaddis@ethionet.et"
        ],
        "Samrawit International": [
            "samrawit@ethionet.et"
        ],
        "Samuel Deressa": [
            "samuelderessa@ethionet.et"
        ],
    }


    ppt_file = "C:/Users/HP/Documents/Pharma_Gebeya_Wholesaler_Manual.pptx"
    send_presentation_email(pharma_companies, ppt_file)
    return HttpResponse("Test email sent successfully", status=200)