from django.db.models import F, Sum


from sales.models import SaleItem



def get_top_products(*, store, date_from, date_to):
    return SaleItem.objects.filter(
        sale__store = store,
        sale__status = 'completed',
        sale__created_at__date__range = [date_from, date_to]
    ).values(
        product_name=F('variant__product__name')
    ).annotate(
        sold_count=Sum('quantity')
    ).order_by(
        '-sold_count'
    )[:10]

