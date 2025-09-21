from rest_framework import serializers
from Medical_device.models import Category
from core.models import Supplier
from .models import SupplierProfile, Industry, City  # Assuming you already have City model

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
        

