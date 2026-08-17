from django.db.models import Sum, Count


from sales.models import Sale, SaleItem




def get_sales_overview(*, store, date_from, date_to):

    sales = Sale.objects.filter(
        store=store,
        status='completed',
        created_at__date__range=[date_from, date_to]
    )

    sales_summary = sales.aggregate(
        orders_count=Count('id'),
        revenue=Sum('total_amount'),
    )
    discount = (
        SaleItem.objects.filter(sale__in=sales).aggregate(
            total=Sum('discount')
        )['total']
        or 0
    )

    return {
        'orders_count': sales_summary['orders_count'],
        'revenue': sales_summary['revenue'] or 0,
        'discount': discount,
    }
