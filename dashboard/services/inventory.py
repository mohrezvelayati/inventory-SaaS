from django.conf import settings
from django.db.models import Sum, Count

from catalog.models import ProductVariant


def get_inventory_overview(*, store):

    return ProductVariant.objects.filter(
        product__store=store
    ).aggregate(
        total_variants=Count('id'),
        total_stock=Sum('current_stock'),
    ) or {'total_variants': 0, 'total_stock': 0}



def get_low_stock_products(store):

    return ProductVariant.objects.filter(
        product__store = store,
        current_stock__lte=settings.LOW_STOCK_THRESHOLD
    ).values(
        'product__name',
        'size',
        'current_stock'
    )
