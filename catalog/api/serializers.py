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
    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'size',
            'purchase_price',
            'sale_price',
            'current_stock',
        ]
        read_only_fields = ['id', 'current_stock']


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
