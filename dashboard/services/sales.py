from django.db.models import Sum


from sales.models import Sale




def get_sales_overview(*, store, date_from, date_to):

    sales = Sale.objects.filter(
        store=store,
        status='completed',
        created_at__date__range=[date_from, date_to]
    )

    return {
        'orders_count': sales.count(),
        'revenue': (
            sales.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        ),
        'discount': (
            sales.aggregate(
                total=Sum('items__discount')
            )['total'] or 0
        )
    }