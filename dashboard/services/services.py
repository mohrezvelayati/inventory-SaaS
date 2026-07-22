from django.utils import timezone
from django.db.models import Sum, Count


from sales.models import Sale



def get_data_range(data_from = None, data_to = None):
    if not data_from:
        data_from = timezone.localdate()

    if not data_to:
        data_to = timezone.localdate()


    return data_from, data_to



def get_sales_summery(*, store, data_from, data_to):
    sales = Sale.objects.filter(
        store = store,
        status = 'completed',
        created_at__date__range = [data_from, data_to]
    )

    return {
        'order_count': sales.count(),
        'total_amount': (
            sales.aggregate(
                total = Sum('total_amount')
            )['total'] or 0
        )
    }





