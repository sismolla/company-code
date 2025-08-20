from rest_framework import serializers
from .models import ChatMessage, ChatThread, DosageForm, Notification, Order, OrderItem, Product, ReportAbuse, Review, UserProducts
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Q
from django.db import transaction

class DosageFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = DosageForm
        fields = ['id', 'name']
from .models import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'whatsapp_link',
            'telegram_link',
            'logo',
            'address',
            'response_time'
        ]
    def get_email(self, obj):
        # Return related user's email if user exists
        return obj.user.email if obj.user else None


class ProductSerializer(serializers.ModelSerializer):
    # supplier = SupplierSerializer(read_only=True)
    dosage_form = DosageFormSerializer(read_only=True)
    class Meta:
        model = Product
        fields = [
            'id',
            'product_id',
            'name',
            'strength',
            'expire_date',
            'price',
            'stock_quantity',
            'dosage_form',
            # 'supplier'
        ]

class ReviewSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = Review
        fields = ['id', 'product', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class ProductDetailSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    supplier = SupplierSerializer(read_only=True)
    dosage_form = serializers.CharField(source='dosage_form.name',read_only=True)
    userproduct_id = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = [
            'id',
            'product_id',
            'name',
            'strength',
            'expire_date',
            'price',
            'stock_quantity',
            'dosage_form',
            'average_rating',
            'image',
            'reviews',
            'supplier',

            'userproduct_id',

        ]
    def get_userproduct_id(self, obj):
        userproduct = getattr(obj.supplier, "user_supplier", None)
        return userproduct.id if userproduct else None


    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None

class ReportAbuseSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = ReportAbuse
        fields = ['product', 'reporter_email', 'reason', 'description']



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class ChatMessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)  # Show username
    class Meta:
        model = ChatMessage
        fields = ['id', 'thread', 'sender', 'message','is_read', 'timestamp',]

from django.utils.timesince import timesince
from django.utils import timezone



class ChatThreadSerializer(serializers.ModelSerializer):
    user_1 = serializers.StringRelatedField(read_only=True)
    user_2 = serializers.StringRelatedField(read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    supplier_logo = serializers.SerializerMethodField()

    seller_last_seen = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ['id', 'user_1', 'user_2', 'created_at', 'messages', 'supplier_logo','seller_last_seen',]

    def get_supplier_logo(self, obj):
        request = self.context.get('request')
        current_user = request.user

        # Identify the "other" user in the thread
        other_user = obj.user_2 if obj.user_1 == current_user else obj.user_1

        # Assuming Supplier model has a OneToOneField to User and a `logo` ImageField
        supplier = getattr(other_user, 'supplier_profile', None)
        if supplier and supplier.logo:
            return request.build_absolute_uri(supplier.logo.url)
        return None

    def get_seller_last_seen(self, obj):
        request_user = self.context['request'].user

        if obj.user_1 == request_user:
            seller_user = obj.user_2
        else:
            seller_user = obj.user_1

        seller_profile = getattr(seller_user, 'seller_profile', None)
        if not seller_profile or not seller_profile.last_activity:
            return None

        return timesince(seller_profile.last_activity, timezone.now()) + " ago"

class ChatThreadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatThread
        fields = ['user_2'] # The user to chat with

    def create(self, validated_data):
        user_1 = self.context['request'].user
        user_2 = validated_data['user_2']

        thread = ChatThread.objects.filter(
            (Q(user_1=user_1) & Q(user_2=user_2)) | 
            (Q(user_1=user_2) & Q(user_2=user_1))
        ).first()

        if not thread:
            # If no thread exists, create a new one
            thread = ChatThread.objects.create(user_1=user_1, user_2=user_2)

        return thread
    

class SupplierSignupSerializer(serializers.ModelSerializer):
    # Fields for User creation
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    
    whatsapp_link = serializers.URLField(required=False, allow_blank=True)
    telegram_link = serializers.URLField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    logo = serializers.ImageField(required=False)
    response_time = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Supplier
        fields = [
            'username', 'email', 'password', 'name', 'phone',
            'whatsapp_link', 'telegram_link', 'logo', 'address', 'response_time'
        ]


    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def create(self, validated_data):
        # Extract user data
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # Create User
        user = User(username=username, email=email)
        user.set_password(password)
        user.save()

        supplier = Supplier.objects.create(user=user, **validated_data)

        return supplier

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")

            # Create or get token

            return {
                'username': user.username,
                'email': user.email
            }

        raise serializers.ValidationError("Both Email and password are required.")

class SingleProductReview(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['reviewer_name', 'rating', 'comment', 'created_at']

class ProductSerializerView(serializers.ModelSerializer):
    dosage_form_name = serializers.CharField(source='dosage_form.name', read_only=True)
    reviews = SingleProductReview(many=True, read_only=True)
    userproduct_id = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'image', 'dosage_form_name', 'dosage_form', 'reviews', 'name', 'price', 'expire_date', 'stock_quantity', 'strength', 'userproduct_id']

    def get_userproduct_id(self, obj):
        userproduct = getattr(obj.supplier, "user_supplier", None)
        return userproduct.id if userproduct else None

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['logo','name','phone','whatsapp_link','telegram_link', 'address' , 'response_time']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['message','created_at','is_read']



class ProductSupplierSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'whatsapp_link',
            'telegram_link',
            'logo',
            'address',
        ]
    def get_email(self, obj):
        # Return related user's email if user exists
        return obj.user.email if obj.user else None
    
class ProductProviderSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()  
    supplier = ProductSupplierSerializer(read_only=True)
    class Meta:
        model = UserProducts
        fields = [
            'id',
            'products',
            'description',
            'supplier',
            'bulk_discount_available',
            'offer_delivery',
        ]

    def get_products(self, obj):
        products = Product.objects.filter(supplier=obj.supplier)
        data = []
        for product in products:
            data.append({
                "product": ProductSerializer(product).data,
                "reviews": ReviewSerializer(product.reviews.all(), many=True).data,
                "average_rating": self.get_average_rating(product),
            })
        return data

    def get_average_rating(self, product):
        reviews = product.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None
    
class SupplierUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProducts
        fields = ['description', 'bulk_discount_available', 'offer_delivery']


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product"
    )

    class Meta:
        model = OrderItem
        fields = ["product_id", "quantity", "price"]

    def validate(self, data):
        product = data["product"]
        quantity = data["quantity"]

        if quantity > product.stock_quantity:  # assuming Product has a 'quantity' field
            raise serializers.ValidationError(
                {"quantity": f"Only {product.quantity} units of {product.name} are available."}
            )
        return data

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_full_name",
            "customer_email_address",
            "customer_phone",
            "customer_pharmacy_name",
            "customer_delivery_address",
            "items",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")

        with transaction.atomic():
            # Infer supplier from the first product
            first_product = items_data[0]["product"]
            supplier = first_product.supplier  

            # Ensure all items have the same supplier
            for item_data in items_data:
                if item_data["product"].supplier != supplier:
                    raise serializers.ValidationError(
                        "All products in one order must be from the same supplier."
                    )

            order = Order.objects.create(supplier=supplier, **validated_data)

            # Create order items and adjust stock
            for item_data in items_data:
                OrderItem.objects.create(order=order, **item_data)

                product = item_data["product"]
                product.stock_quantity -= item_data["quantity"]
                product.save()

        return order


class SupplierOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_dosage = serializers.CharField(source='product.dosage_form', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product','product_dosage', 'product_name', 'product_price', 'quantity', 'price']


# Order serializer including nested items
class SupplierOrderSerializer(serializers.ModelSerializer):
    items = SupplierOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'customer_full_name',
            'customer_email_address',
            'customer_phone',
            'customer_pharmacy_name',
            'customer_delivery_address',
            'supplier',
            'status',
            'created_at',
            'items',   # include nested order items
            'is_active'
        ]


    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get("status", old_status)

        if old_status != new_status:
            if new_status == "cancelled":
                instance.is_active = False  # <--- set the Order inactive
                instance.save(update_fields=['is_active'])
                
                for item in instance.items.all():
                    item.is_active = False
                    item.save()
                    product = item.product
                    product.stock_quantity += item.quantity
                    product.save()

            elif old_status == "cancelled" and new_status in ["confirmed", "pending"]:
                instance.is_active = True  # reactivate the order
                instance.save(update_fields=['is_active'])
                
                for item in instance.items.all():
                    product = item.product
                    product.stock_quantity -= item.quantity
                    product.save()

        return super().update(instance, validated_data)
