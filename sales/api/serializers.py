from rest_framework import serializers

from catalog.models import ProductVariant



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



class SaleCreateSerializer(serializers.Serializer):

    customer = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    channel = serializers.CharField()
    payment_method = serializers.CharField()
    items = SaleItemInputSerializer(many=True)