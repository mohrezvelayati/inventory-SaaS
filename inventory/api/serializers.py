from rest_framework import serializers

from inventory.models import InventoryMovement
from catalog.models import ProductVariant
from stores.services import get_current_membership, MembershipResolutionError



class InventoryMovementSerializer(serializers.ModelSerializer):
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.none()
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return

        self.fields['variant'].queryset = ProductVariant.objects.filter(
            product__store_id=membership.store_id
        )



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