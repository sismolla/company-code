from rest_framework import serializers
from .models import Category, Attribute, Product, ProductAttributeValue, Attribute, ProductImage

class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "name", "field_type", "options"]

class CategorySerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "attributes"]



class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.ReadOnlyField(source="attribute.name")
    attribute_field_type = serializers.ReadOnlyField(source="attribute.field_type")

    class Meta:
        model = ProductAttributeValue
        fields = ["id", "attribute", "attribute_name", "attribute_field_type", "value"]


class ProductSerializer(serializers.ModelSerializer):
    attributes = ProductAttributeValueSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "manufacturer",
            "brand",
            "model_number",
            "intended_use",
            "description",
            "certifications",
            "brochure",
            "warranty",
            "price",
            "created_at",
            "attributes",
            "images",
        ]
        read_only_fields = ["created_at"]
