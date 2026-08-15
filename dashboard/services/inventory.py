from django.conf import settings

from catalog.models import ProductVariant


def get_inventory_overview(*, store):

    variants = ProductVariant.objects.filter(
        product__store=store
    )

    return {
        'total_variants': variants.count(),
        'total_stock': sum(
            v.current_stock
            for v in variants
        )
    }



def get_low_stock_products(store):

    return ProductVariant.objects.filter(
        product__store = store,
        current_stock__lte=settings.LOW_STOCK_THRESHOLD
    ).values(
        'product__name',
        'size',
        'current_stock'
    )
