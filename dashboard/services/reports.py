from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate

from catalog.models import ProductVariant
from sales.models import Sale, SaleItem


MONEY_FIELD = DecimalField(max_digits=20, decimal_places=0)


def get_store_report(*, store, date_from, date_to):
    sales = Sale.objects.filter(
        store=store,
        status=Sale.StatusChoices.COMPLETED,
        created_at__date__range=(date_from, date_to),
    )
    items = SaleItem.objects.filter(sale__in=sales)

    sales_totals = sales.aggregate(
        orders_count=Count('id'),
        revenue=Sum('total_amount'),
    )
    item_totals = items.aggregate(
        discount=Sum('discount'),
        cost=Sum(
            F('unit_cost') * F('quantity'),
            output_field=MONEY_FIELD,
        ),
    )
    orders_count = sales_totals['orders_count'] or 0
    revenue = sales_totals['revenue'] or Decimal('0')
    discount = item_totals['discount'] or Decimal('0')
    cost = item_totals['cost'] or Decimal('0')

    daily_rows = {
        row['date']: row
        for row in sales.annotate(date=TruncDate('created_at')).values('date').annotate(
            orders_count=Count('id'),
            revenue=Sum('total_amount'),
        )
    }
    daily = []
    current_date = date_from
    while current_date <= date_to:
        row = daily_rows.get(current_date, {})
        daily.append({
            'date': current_date,
            'orders_count': row.get('orders_count', 0),
            'revenue': row.get('revenue') or Decimal('0'),
        })
        current_date += timedelta(days=1)

    channel_rows = {
        row['channel']: row
        for row in sales.values('channel').annotate(
            orders_count=Count('id'),
            revenue=Sum('total_amount'),
        )
    }
    channels = [
        {
            'channel': channel,
            'orders_count': channel_rows.get(channel, {}).get('orders_count', 0),
            'revenue': channel_rows.get(channel, {}).get('revenue') or Decimal('0'),
        }
        for channel in Sale.ChannelChoices.values
    ]

    products = list(
        items.values(product_name=F('variant__product__name')).annotate(
            sold_count=Sum('quantity'),
            revenue=Sum('final_price'),
        ).order_by('-sold_count', 'product_name')[:10]
    )

    variants = ProductVariant.objects.filter(product__store=store)
    inventory_totals = variants.aggregate(
        total_variants=Count('id'),
        total_stock=Sum('current_stock'),
        purchase_value=Sum(
            F('purchase_price') * F('current_stock'),
            output_field=MONEY_FIELD,
        ),
        retail_value=Sum(
            F('sale_price') * F('current_stock'),
            output_field=MONEY_FIELD,
        ),
    )

    return {
        'period': {'date_from': date_from, 'date_to': date_to},
        'sales': {
            'orders_count': orders_count,
            'revenue': revenue,
            'discount': discount,
            'cost': cost,
            'gross_profit': revenue - cost,
            'average_order': revenue / orders_count if orders_count else Decimal('0'),
        },
        'daily': daily,
        'channels': channels,
        'products': products,
        'inventory': {
            'total_variants': inventory_totals['total_variants'] or 0,
            'total_stock': inventory_totals['total_stock'] or 0,
            'low_stock_count': variants.filter(
                current_stock__gt=0,
                current_stock__lte=settings.LOW_STOCK_THRESHOLD,
            ).count(),
            'out_of_stock_count': variants.filter(current_stock=0).count(),
            'purchase_value': inventory_totals['purchase_value'] or Decimal('0'),
            'retail_value': inventory_totals['retail_value'] or Decimal('0'),
        },
    }
