from rest_framework import serializers

from inventory.models import InventoryMovement
from catalog.models import ProductVariant


class InventoryMovementSerializer(serializers.ModelSerializer):

    class Meta:
        model = InventoryMovement
        fields = [
            'id',
            'variant',
            'quantity',
            'movement_type',
            'note',
            'created_at',
        ]


    read_only_fields = ['id', 'created_at']



class InventorySerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    class Meta:
        model = ProductVariant

        fields = [
            'id',
            'product_name',
            'size',
            'current_stock',
        ]