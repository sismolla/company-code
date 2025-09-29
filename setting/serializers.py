from rest_framework import serializers
from Medical_device.models import Category
from django.utils import timezone
from datetime import timedelta
from .models import QuoteImage, QuoteRequest, SupplierProfile, Industry, City  # Assuming you already have City model
from .models import UserConnection
from django.contrib.auth import get_user_model
User = get_user_model()


class SupplierProfileSerializer(serializers.ModelSerializer):
    industries = serializers.PrimaryKeyRelatedField(
        queryset=Industry.objects.all(), many=True, required=False
    )
    cities = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), many=True, required=False
    )
    
    class Meta:
        model = SupplierProfile
        fields = ['user', 'industries', 'specialized_equipment', 'cities']
        read_only_fields = ['user']  # user will be set from request.user

    def create(self, validated_data):
        industries = validated_data.pop('industries', [])
        specialized_equipment = validated_data.pop('specialized_equipment', [])
        cities = validated_data.pop('cities', [])
        
        supplier = self.context['request'].user
        profile, created = SupplierProfile.objects.get_or_create(user=supplier)
        
        # Assign ManyToMany fields
        profile.industries.set(industries)
        profile.specialized_equipment.set(specialized_equipment)
        profile.cities.set(cities)
        profile.save()
        return profile

    def update(self, instance, validated_data):
        industries = validated_data.pop('industries', None)
        specialized_equipment = validated_data.pop('specialized_equipment', None)
        cities = validated_data.pop('cities', None)

        # Update ManyToMany fields if provided
        if industries is not None:
            instance.industries.set(industries)
        if specialized_equipment is not None:
            instance.specialized_equipment.set(specialized_equipment)
        if cities is not None:
            instance.cities.set(cities)

        instance.save()
        return instance



class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ['id', 'name']

class SpecializedEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name']
        


class UserConnectionSerializer(serializers.ModelSerializer):
    follower = serializers.HiddenField(default=serializers.CurrentUserDefault())
    following = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = UserConnection
        fields = ["id", "follower", "following", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, data):
        follower = data["follower"]
        following = data["following"]

        if follower == following:
            raise serializers.ValidationError("You cannot follow yourself.")

        if UserConnection.objects.filter(follower=follower, following=following).exists():
            raise serializers.ValidationError("You already follow this user.")

        return data

    def create(self, validated_data):
        return UserConnection.objects.create(**validated_data)

# serializers.py
class QuoteImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteImage
        fields = ["id", "image"]

from django.db import transaction

class QuoteRequestSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    supplier_address = serializers.CharField(source="supplier.address", read_only=True)
    images = QuoteImageSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteRequest
        fields = [
            "id", "quote_id",
            "supplier_name",
            "supplier_address",
            "message",
            "attachment",
            "images",
            "created_at",
            "expiry_date",
            "is_active",
            "status_badge",
        ]
        read_only_fields = [
            "quote_id", "created_at", "expiry_date",
            "is_active", "status_badge", "supplier_name", "supplier_address"
        ]

    def create(self, validated_data):
        """
        Handle new QuoteRequest with optional attachment + images
        """
        request = self.context.get("request")

        # Create the main quote
        quote_request = QuoteRequest.objects.create(**validated_data)

        # ✅ Handle attachment
        if "attachment" in request.FILES:
            quote_request.attachment = request.FILES["attachment"]

        # ✅ Handle images
        images = request.FILES.getlist("images")
        if images:
            if len(images) > 3:
                raise serializers.ValidationError("You can upload at most 3 images.")
            for img in images:
                if img.size > 5 * 1024 * 1024:  # 5MB check (matches JS)
                    raise serializers.ValidationError("Each image must be ≤ 5MB.")
                QuoteImage.objects.create(quote_request=quote_request, image=img)

        quote_request.save()
        return quote_request

    def update(self, instance, validated_data):
        """
        Handle editing an existing QuoteRequest
        """
        request = self.context['request']

        # ✅ Update message
        instance.message = validated_data.get("message", instance.message)

        # ✅ Attachment handling
        remove_attachment = request.data.get("remove_attachment", "false").lower() == "true"
        if remove_attachment and instance.attachment:
            instance.attachment.delete(save=False)
            instance.attachment = None
        elif "attachment" in request.FILES:
            if instance.attachment:
                instance.attachment.delete(save=False)
            instance.attachment = request.FILES["attachment"]

        # ✅ Delete specific images
        removed_images = request.data.getlist("removed_images")  # ["id1", "id2"]
        if removed_images:
            instance.images.filter(id__in=removed_images).delete()

        # ✅ Add new images
        new_images = request.FILES.getlist("images")
        if new_images:
            if instance.images.count() + len(new_images) > 3:
                raise serializers.ValidationError("You can have at most 3 images total.")
            for image in new_images:
                if image.size > 5 * 1024 * 1024:
                    raise serializers.ValidationError("Each image must be ≤ 5MB.")
                QuoteImage.objects.create(quote_request=instance, image=image)

        instance.save()
        return instance
