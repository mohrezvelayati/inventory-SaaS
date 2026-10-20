from rest_framework import serializers

from catalog.models import Product
from customers.models import Customer
from stores.services import get_current_membership, MembershipResolutionError

from wanted.models import WantedCustomerRequest, WantedProduct

class WantedSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.none(),
        required=False,
        allow_null=True
    )
    product_name_display = serializers.CharField(
        source='product.name', read_only=True
    )

    class Meta:
        model = WantedProduct
        fields = [
            "id",
            "product",
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

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            try:
                membership = get_current_membership(request.user)

                self.fields["product"].queryset = Product.objects.filter(
                    store=membership.store
                )

                if "customer" in self.fields:
                    self.fields["customer"].queryset = Customer.objects.filter(
                        store=membership.store
                    )

            except MembershipResolutionError:
                pass


class WantedCreateSerializer(WantedSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.none(),
        write_only=True,
    )

    class Meta(WantedSerializer.Meta):
        fields = [
            *WantedSerializer.Meta.fields,
            "customer",
        ]


class WantedCustomerRequestSerializer(serializers.ModelSerializer):
    customer = serializers.IntegerField(
        source="customer_id",
        read_only=True,
        allow_null=True,
    )
    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
        allow_null=True,
    )
    customer_phone_number = serializers.CharField(
        source="customer.phone_number",
        read_only=True,
        allow_null=True,
    )
    created_by = serializers.IntegerField(
        source="created_by_id",
        read_only=True,
        allow_null=True,
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = WantedCustomerRequest
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone_number",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields
