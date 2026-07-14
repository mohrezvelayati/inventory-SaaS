from rest_framework import serializers

from catalog.models import Category, Product, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at']
        
        read_only_fields = ['id', 'created_at']




class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'variants', 'created_at']
        read_only_fields = ['id', 'variants', 'created_at']




class ProductVariantSerializer(serializers.ModelSerializer):    
    
    class Meta:
        model = ProductVariant
        
        fields = [
                'id',
                'size',
                'purchase_price',
                'sale_price',
                'current_stock'
            ]

        read_only_fields = ['id', 'current_stock']




class ProductVariantSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductVariant

        fields = [
            'id',
            'size',
            'purchase_price',
            'sale_price',
            'current_stock',
        ]

        read_only_fields = [
            'id',
            'current_stock',
        ]