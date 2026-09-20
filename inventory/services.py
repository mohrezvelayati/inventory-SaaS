from django.db import transaction
from rest_framework.exceptions import ValidationError

from inventory.models import InventoryMovement
from catalog.models import Product, ProductVariant
from catalog.services import create_variant
from dashboard.cache import schedule_dashboard_cache_invalidation


@transaction.atomic
def create_inventory_movement(
    *,
    store,
    variant,
    quantity,
    movement_type,
    user,
    note='',
    invalidate_dashboard=True,
):
    if movement_type not in InventoryMovement.MovementType.values:
        raise ValidationError({
            'movement_type': 'Invalid inventory movement type.'
        })

    if quantity == 0:
        raise ValidationError({
            'quantity': 'Quantity cannot be zero.'
        })

    if (
        movement_type == InventoryMovement.MovementType.PURCHASE
        and quantity < 0
    ):
        raise ValidationError({
            'quantity': 'Purchase quantity must be positive.'
        })

    if (
        movement_type == InventoryMovement.MovementType.SALE
        and quantity > 0
    ):
        raise ValidationError({
            'quantity': 'Sale quantity must be negative.'
        })

    variant = (
        ProductVariant.objects
        .select_for_update(of=('self',))
        .select_related('product')
        .get(pk=variant.pk)
    )

    if variant.product.store_id != store.id:
        raise ValidationError({
            'variant': 'The selected variant does not belong to this store.'
        })
    new_stock = variant.current_stock + quantity

    if new_stock < 0:
        raise ValidationError({'quantity': 'Insufficient stock.'})
    
    variant.current_stock = new_stock
    variant.save(update_fields=['current_stock'])


    movement = InventoryMovement.objects.create(
        variant = variant,
        quantity = quantity,
        movement_type = movement_type,
        note = note,
        created_by = user, 
    )

    if invalidate_dashboard:
        schedule_dashboard_cache_invalidation(store.id)

    return movement


@transaction.atomic
def create_batch_purchase(
    *,
    store,
    product,
    items,
    user,
    purchase_price=None,
    sale_price=None,
    note='',
):
    try:
        product = (
            Product.objects
            .select_for_update()
            .get(pk=product.pk, store_id=store.id)
        )
    except Product.DoesNotExist as error:
        raise ValidationError({
            'product': 'The selected product does not belong to this store.'
        }) from error

    variants_by_size = {
        variant.size: variant
        for variant in (
            ProductVariant.objects
            .select_for_update()
            .filter(product=product)
        )
    }
    movements = []

    for item in items:
        size = item['size']
        variant = variants_by_size.get(size)

        if variant is None:
            if purchase_price is None or sale_price is None:
                message = 'Purchase and sale prices are required for new sizes.'
                raise ValidationError({
                    'purchase_price': message,
                    'sale_price': message,
                })

            variant = create_variant(
                product=product,
                size=size,
                purchase_price=purchase_price,
                sale_price=sale_price,
                invalidate_dashboard=False,
            )
            variants_by_size[size] = variant

        movement = create_inventory_movement(
            store=store,
            variant=variant,
            quantity=item['quantity'],
            movement_type=InventoryMovement.MovementType.PURCHASE,
            user=user,
            note=note,
            invalidate_dashboard=False,
        )
        movements.append(movement)

    schedule_dashboard_cache_invalidation(store.id)

    return movements
