from rest_framework import serializers

from inventory.models import InventoryMovement
from catalog.models import ProductVariant
from stores.services import get_current_membership, MembershipResolutionError



class InventoryMovementCreateSerializer(serializers.ModelSerializer):
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.none()
    )
    movement_type = serializers.ChoiceField(
        choices=[
            InventoryMovement.MovementType.PURCHASE,
            InventoryMovement.MovementType.ADJUSTMENT,
        ]
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

    def validate(self, attrs):
        quantity = attrs['quantity']
        movement_type = attrs['movement_type']

        if quantity == 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity cannot be zero.'
            })

        if (
            movement_type == InventoryMovement.MovementType.PURCHASE
            and quantity < 0
        ):
            raise serializers.ValidationError({
                'quantity': 'Purchase quantity must be positive.'
            })

        return attrs


class BatchPurchaseItemSerializer(serializers.Serializer):
    size = serializers.CharField(max_length=50, trim_whitespace=True)
    quantity = serializers.IntegerField(min_value=1)

    def validate_size(self, value):
        if not value:
            raise serializers.ValidationError('Size cannot be blank.')
        return value


class BatchInventoryPurchaseSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    sale_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=0,
        required=False,
    )
    note = serializers.CharField(required=False, allow_blank=True, default='')
    items = BatchPurchaseItemSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        sizes = [item['size'] for item in items]
        if len(sizes) != len(set(sizes)):
            raise serializers.ValidationError(
                'Each size may appear only once.'
            )
        return items


class BatchPurchaseResultItemSerializer(serializers.Serializer):
    movement = serializers.IntegerField()
    variant = serializers.IntegerField()
    size = serializers.CharField()
    quantity = serializers.IntegerField()
    current_stock = serializers.IntegerField()


class BatchInventoryPurchaseResponseSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    items = BatchPurchaseResultItemSerializer(many=True)


class InventoryMovementHistorySerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source='variant.product_id',
        read_only=True,
    )
    product_name = serializers.CharField(
        source='variant.product.name',
        read_only=True,
    )
    variant_size = serializers.CharField(
        source='variant.size',
        read_only=True,
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = InventoryMovement
        fields = [
            'id',
            'product_id',
            'product_name',
            'variant',
            'variant_size',
            'quantity',
            'movement_type',
            'created_by',
            'created_by_username',
            'note',
            'created_at',
        ]
        read_only_fields = fields



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
