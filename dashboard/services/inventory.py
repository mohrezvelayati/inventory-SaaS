from django.conf import settings
from django.db.models import Count, F, Sum

from catalog.models import ProductVariant


def get_inventory_overview(*, store):

    overview = ProductVariant.objects.filter(
        product__store=store
    ).aggregate(
        total_variants=Count('id'),
        total_stock=Sum('current_stock'),
    )

    return {
        'total_variants': overview['total_variants'],
        'total_stock': overview['total_stock'] or 0,
    }



def get_low_stock_products(store):

    return ProductVariant.objects.filter(
        product__store = store,
        current_stock__lte=settings.LOW_STOCK_THRESHOLD
    ).values(
        'size',
        'current_stock'
    ).annotate(
        product_name=F('product__name')
    )
