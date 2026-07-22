from wanted.models import WantedProduct




def get_top_wanted(*, store):
    return WantedProduct.objects.filter(
        store=store,
    ).order_by(
        '-wanted_count'
    ).values(
        'product_name',
        'size',
        'wanted_count'
    )[:10]