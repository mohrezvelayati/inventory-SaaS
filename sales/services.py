from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from sales.models import Sale, SaleItem
from inventory.services import create_inventory_movement
from catalog.models import ProductVariant


### Create empty sale (Draft) ###
@transaction.atomic
def create_sale(*, store, seller, customer=None, channel, payment_method):
    if customer is not None and customer.store_id != store.id:
        raise ValidationError('The selected customer does not belong to this store')

    sale = Sale.objects.create(
        store=store,
        seller=seller,
        customer=customer,
        channel=channel,
        payment_method=payment_method,
        status=Sale.StatusChoices.DRAFT,
        total_amount=0,
    )

    return sale

@transaction.atomic
def delete_draft_sale(*, sale):
    locked_sale = (
        Sale.objects
        .select_for_update()
        .get(pk=sale.pk)
    )

    if locked_sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError({
            'sale': 'Only draft sales can be deleted.'
        })

    locked_sale.delete()


### Add item to sale ###
@transaction.atomic
def add_sale_item(*, sale, variant, quantity, discount=0):
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError(
           "It is not possible to modify a completed sale."
        )

    if variant.product.store_id != sale.store_id:
        raise ValidationError(
            'The selected variant does not belong to the store of this sale.'
        )

    if quantity <= 0:
        raise ValidationError(
            'The value must be greater than zero.'
        )
    
    # Get the current selling price
    unit_price = variant.sale_price
    line_subtotal = unit_price * quantity

    if discount < 0:
        raise ValidationError({
            "discount": "Discount cannot be negative."
        })

    if discount > line_subtotal:
        raise ValidationError({
            "discount": "Discount cannot exceed the line subtotal."
        })

    line_total = line_subtotal - discount


    sale_item = SaleItem.objects.create(
        sale=sale,
        variant=variant,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        final_price=line_total
    )


    update_sale_total(sale)

    return sale_item


@transaction.atomic
def update_sale_item(*, sale_item, quantity=None, discount=None):
    sale = Sale.objects.select_for_update().get(pk=sale_item.sale_id)

    if sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError('Only draft sales can be modified.')

    sale_item = SaleItem.objects.select_for_update().get(pk=sale_item.pk, sale_id=sale.id)

    if quantity is None:
        quantity = sale_item.quantity

    if discount is None:
        discount = sale_item.discount

    if quantity <= 0:
        raise ValidationError({
            'quantity': 'Quantity must be greater than zero.'
        })

    if discount < 0:
        raise ValidationError({
            'discount': 'Discount cannot be negative.'
        })

    line_subtotal = sale_item.unit_price * quantity

    if discount > line_subtotal:
        raise ValidationError({
            'discount': 'Discount cannot exceed the line subtotal.'
        })

    sale_item.quantity = quantity
    sale_item.discount = discount
    sale_item.final_price = line_subtotal - discount

    sale_item.save(
        update_fields=[
            'quantity',
            'discount',
            'final_price',
        ]
    )

    update_sale_total(sale)

    return sale_item


@transaction.atomic
def delete_sale_item(*, sale_item):
    sale = Sale.objects.select_for_update().get(pk=sale_item.sale_id)

    if sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError(
            'Only draft sales can be modified.'
        )

    locked_sale_item = SaleItem.objects.select_for_update().get(
        pk=sale_item.pk,
        sale_id=sale.id,
    )

    locked_sale_item.delete()
    update_sale_total(sale)


### Update sale total amount ###
def update_sale_total(sale):
    total = (
        sale.items.aggregate(
            total = Sum('final_price')
        )["total"]
        or 0
    )

    sale.total_amount = total

    sale.save(update_fields=['total_amount'])

    return total



### Stock Validation ###
def validate_sale_stock(*, required_quantities, locked_variants):
    errors = []

    for requirement in required_quantities:
        variant = locked_variants[requirement['variant_id']]
        requested_quantity = requirement['quantity']
        available_stock = variant.current_stock

        if available_stock < requested_quantity:
            errors.append(
                {
                    "variant": variant.id,
                    "product": variant.product.name,
                    "requested": requested_quantity,
                    "available": available_stock,
                }
            )

    if errors:
        raise ValidationError(
            {
                'stock_error':errors
            }
        )
    
    return True



### Complete Sale ###
@transaction.atomic
def complete_sale(*, sale, user):
    sale = Sale.objects.select_for_update().get(pk=sale.pk) # Fetch and lock the sale to prevent concurrent completion

    if sale.status != Sale.StatusChoices.DRAFT :
        raise ValidationError(
            "فقط فروش درحال تکمیل می‌تواند تکمیل شود"
        )
    items = sale.items.all()


    if not items.exists():
        raise ValidationError(
            "نمی‌توان فروش خالی را تکمیل کرد"
        )

    required_quantities = list(
        items.values('variant_id')
        .annotate(quantity=Sum('quantity'))
        .order_by('variant_id')
    )

    variant_ids = [
        row['variant_id']
        for row in required_quantities
    ]


    locked_variants = {
        variant.id: variant
        for variant in (
            ProductVariant.objects
            .select_for_update()
            .select_related('product')
            .filter(id__in=variant_ids)
            .order_by('id')
        )
    }

    
    validate_sale_stock(
        required_quantities=required_quantities,
        locked_variants=locked_variants,
        )

    # کاهش موجودی
    for item in items:
        create_inventory_movement(
            store=sale.store,
            variant=locked_variants[item.variant_id],
            quantity=-item.quantity,
            movement_type='sale',
            user=user,
            note=f"Sale #{sale.id}"
        )

    sale.status = Sale.StatusChoices.COMPLETED

    sale.save(update_fields = ['status'])

    return sale



### Cancel Sale ###
@transaction.atomic
def cancel_sale(*, sale, user):
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if sale.status != Sale.StatusChoices.COMPLETED:
        raise ValidationError("فقط فروش تکمیل شده قابل کنسل شدن است")
    for item in sale.items.all():
        create_inventory_movement(
            store=sale.store,
            variant=item.variant,
            quantity=item.quantity,
            movement_type='adjustment',
            user=user,
            note=f"Cancellation of Sale #{sale.id}"
        )
    sale.status = Sale.StatusChoices.CANCELLED
    sale.save(update_fields=['status'])
    return sale
