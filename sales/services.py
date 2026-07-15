from django.db import transaction

from sales.models import Sale, SaleItem
from inventory.services import create_inventory_movement



@transaction.atomic
def create_sale(*, store, seller, customer, channel, payment_method, items):

    total_amount = 0

    sale = Sale.objects.create(
        store=store,
        seller=seller,
        customer=customer,
        channel=channel,
        payment_method=payment_method,
        total_amount=0
    )

    for item in items:
        variant = item['variant']
        quantity = item['quantity']
        discount = item.get('discount', 0)
        unit_price = variant.sale_price
        final_price = (unit_price * quantity) - discount

        SaleItem.objects.create(
            sale=sale,
            variant=variant,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            final_price=final_price
        )

        total_amount += final_price


        create_inventory_movement(
            variant=variant,
            quantity=quantity,
            movement_type='sale',
            user=seller.user,
            note=f"Sale #{sale.id}",
        )

    
    sale.total_amount = total_amount
    sale.save()


    return sale