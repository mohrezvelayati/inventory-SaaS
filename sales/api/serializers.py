from rest_framework import serializers

from catalog.models import ProductVariant
from sales.models import Sale, SaleItem
from customers.models import Customer



class SaleItemInputSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all()
    )

    quantity = serializers.IntegerField(
        min_value=1
    )

    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False,
        default=0
    )




class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    size = serializers.CharField(source='variant.size', read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id",
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

    customer = serializers.PrimaryKeyRelatedField(
    queryset=Customer.objects.all(),
    required=False,
    allow_null=True
    )
    channel = serializers.ChoiceField(choices=Sale.ChannelChoices.choices)
    payment_method = serializers.ChoiceField(choices=Sale.PaymentChoices.choices, required=False, allow_null=True)



class SaleItemCreateSerializer(serializers.Serializer):

    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all()
    )

    quantity = serializers.IntegerField(
        min_value=1
    )

    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        required=False,
        default=0
    )