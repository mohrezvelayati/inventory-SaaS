from rest_framework import serializers

from catalog.models import ProductVariant
from sales.models import Sale, SaleItem
from customers.models import Customer
from stores.services import get_current_membership, MembershipResolutionError



class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    size = serializers.CharField(source='variant.size', read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "variant",
            "product_name",
            "size",
            "quantity",
            "unit_price",
            "discount",
            "final_price",
        ]



class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(
        many = True,
        read_only = True,
    )

    class Meta:
        model = Sale

        fields = [
            "id",
            "customer",
            "channel",
            "payment_method",
            "status",
            "total_amount",
            "items",
            "created_at"
        ]


class SaleCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.none(), required=False, allow_null=True)
    channel = serializers.ChoiceField(choices=Sale.ChannelChoices.choices)
    payment_method = serializers.ChoiceField(choices=Sale.PaymentChoices.choices)
    status = serializers.ChoiceField(choices=Sale.StatusChoices.choices, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return

        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return

        self.fields['customer'].queryset = Customer.objects.filter(store_id=membership.store_id)


class SaleItemCreateSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='variant.product.name', read_only=True
    )
    size = serializers.CharField(source='variant.size', read_only=True)
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )
    final_price = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "variant",
            "product_name",
            "size",
            "quantity",
            "unit_price",
            "discount",
            "final_price",
        ]
        read_only_fields = ["id", "product_name", "size", "unit_price", "final_price"]

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


class SaleItemUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    variant = serializers.PrimaryKeyRelatedField(read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    size = serializers.CharField(source='variant.size', read_only=True)
    quantity = serializers.IntegerField(min_value=1, required=False)
    discount = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0, required=False)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Provide quantity or discount.')

        return attrs