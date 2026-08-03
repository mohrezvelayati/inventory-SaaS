from rest_framework import serializers

from catalog.models import Product
from customers.models import Customer
from stores.services import get_current_membership, MembershipResolutionError

from wanted.models import WantedProduct



class WantedSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.none(),
        required=False,
        allow_null=True
    )
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.none(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    product_name_display = serializers.CharField(
        source='product.name', read_only=True
    )

    class Meta:
        model = WantedProduct
        fields = [
            "id",
            "product",
            "customer",
            "product_name",
            "product_name_display",
            "brand",
            "size",
            "wanted_count",
            "created_at",
        ]

        read_only_fields = [
            'id',
            'wanted_count',
            'created_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                membership = get_current_membership(request.user)
                self.fields["product"].queryset = Product.objects.filter(
                    store=membership.store
                )
                self.fields['customer'].queryset = Customer.objects.filter(
                    store=membership.store
                )
            except MembershipResolutionError:
                pass
