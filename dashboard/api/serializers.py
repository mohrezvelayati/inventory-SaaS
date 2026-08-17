from django.conf import settings
from django.utils import timezone
from rest_framework import serializers


class DashboardQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        date_from = attrs.get('date_from', today)
        date_to = attrs.get('date_to', today)

        if date_from > date_to:
            raise serializers.ValidationError({
                'date_to': 'date_to must be on or after date_from.'
            })

        if (
            date_to - date_from
        ).days > settings.DASHBOARD_MAX_DATE_RANGE_DAYS:
            raise serializers.ValidationError({
                'date_to': (
                    'Dashboard date range cannot exceed '
                    f'{settings.DASHBOARD_MAX_DATE_RANGE_DAYS} days.'
                )
            })

        attrs['date_from'] = date_from
        attrs['date_to'] = date_to
        return attrs


class SalesOverviewSerializer(serializers.Serializer):
    orders_count = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=0)
    discount = serializers.DecimalField(max_digits=12, decimal_places=0)


class InventoryOverviewSerializer(serializers.Serializer):
    total_variants = serializers.IntegerField()
    total_stock = serializers.IntegerField()


class LowStockProductSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    size = serializers.CharField()
    current_stock = serializers.IntegerField()


class TopProductSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    sold_count = serializers.IntegerField()


class TopWantedSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    size = serializers.CharField()
    wanted_count = serializers.IntegerField()


class DashboardResponseSerializer(serializers.Serializer):
    sales = SalesOverviewSerializer()
    inventory = InventoryOverviewSerializer()
    low_stock = LowStockProductSerializer(many=True)
    products = TopProductSerializer(many=True)
    wanted = TopWantedSerializer(many=True)
