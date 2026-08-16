from django.db.models import Sum, Count


from sales.models import Sale




def get_sales_overview(*, store, date_from, date_to):

    sales = Sale.objects.filter(
        store=store,
        status='completed',
        created_at__date__range=[date_from, date_to]
    )

    agg = sales.aggregate(
        orders_count=Count('id'),
        revenue=Sum('total_amount'),
        discount=Sum('items__discount'),
    ) or {'orders_count': 0, 'revenue': 0, 'discount': 0}

    return {
        'orders_count': agg['orders_count'],
        'revenue': agg['revenue'],
        'discount': agg['discount'],
    }
