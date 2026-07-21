from rest_framework import serializers

from wanted.models import WantedProduct



class WantedSerializer(serializers.ModelSerializer):

    product_name_display = serializers.CharField(source='product.name', read_only=True)

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