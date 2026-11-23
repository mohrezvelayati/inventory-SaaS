from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import Product
from customers.models import Customer
from stores.services import get_current_membership, MembershipResolutionError

from wanted.models import WantedCustomerRequest, WantedProduct

class WantedSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
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
            "cover_image",
            "created_at",
        ]

        read_only_fields = [
            'id',
            'wanted_count',
            'cover_image',
            'created_at',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_cover_image(self, wanted_product):
        image_name = getattr(
            wanted_product,
            'latest_request_image',
            None,
        )

        if image_name:
            storage = WantedCustomerRequest._meta.get_field('image').storage
            image_url = storage.url(image_name)
        elif (
            wanted_product.product_id
            and wanted_product.product.image
        ):
            image_url = wanted_product.product.image.url
        else:
            return None

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(image_url)
        return image_url

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
    image = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta(WantedSerializer.Meta):
        fields = [
            *WantedSerializer.Meta.fields,
            "customer",
            "image",
        ]

    def validate_image(self, image):
        if image is None:
            return image

        if image.size > settings.IMAGE_UPLOAD_MAX_SIZE_BYTES:
            max_size_mb = settings.IMAGE_UPLOAD_MAX_SIZE_BYTES // (1024 * 1024)
            raise serializers.ValidationError(
                f'Image size cannot exceed {max_size_mb} MB.'
            )

        return image


class WantedCustomerRequestSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True, allow_null=True)
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
            "image",
            "created_at",
        ]
        read_only_fields = fields
