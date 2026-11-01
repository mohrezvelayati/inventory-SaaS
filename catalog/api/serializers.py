from rest_framework import serializers

from catalog.models import Category, Product, ProductVariant
from stores.services import get_current_membership, MembershipResolutionError


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, name):
        request = self.context.get('request')

        if request is None or not request.user.is_authenticated:
            return name

        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            raise serializers.ValidationError(
                "Store not found."
            )

        categories = Category.objects.filter(store_id=membership.store_id, name=name,)

        if self.instance is not None:
            categories = categories.exclude(
                pk=self.instance.pk
            )

        if categories.exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )

        return name

class ProductVariantSerializer(serializers.ModelSerializer):
    size = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
        required=False,
        allow_null=True,
        allow_blank=False,
    )
    without_size = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'size',
            'without_size',
            'purchase_price',
            'sale_price',
            'current_stock',
        ]
        read_only_fields = ['id', 'current_stock']

    def validate(self, attrs):
        default_without_size = (
            self.instance.size is None
            if self.instance is not None
            else False
        )
        without_size = attrs.pop('without_size', default_without_size)
        size_was_provided = 'size' in attrs
        size = attrs.get(
            'size',
            self.instance.size if self.instance is not None else None,
        )

        if without_size:
            if size_was_provided and size is not None:
                raise serializers.ValidationError({
                    'size': 'Do not provide size when without_size is true.'
                })
            attrs['size'] = None
        elif size is None:
            raise serializers.ValidationError({
                'size': 'Size is required when without_size is false.'
            })

        return attrs


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=Category.objects.none(),
        many=True,
        required=False,
    )
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'categories',
            'variants',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'variants',
            'created_at',
            'updated_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return

        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            return

        self.fields['categories'].child_relation.queryset = (
            Category.objects.filter(store_id=membership.store_id)
        )


class ProductSalePriceUpdateSerializer(serializers.Serializer):
    sale_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=0,
    )
