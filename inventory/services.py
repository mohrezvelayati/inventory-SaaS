from django.db import transaction
from django.core.exceptions import ValidationError

from inventory.models import InventoryMovement
from catalog.models import ProductVariant



@transaction.atomic
def create_inventory_movement(*, store, variant, quantity, movement_type, user, note=""):
    variant = (
        ProductVariant.objects
        .select_for_update(of=('self',))
        .select_related('product')
        .get(pk=variant.pk)
    )

    if variant.product.store_id != store.id:
        raise ValidationError(
            'The selected variant does not belong to this store.'
        )
    new_stock = variant.current_stock + quantity

    if new_stock < 0:
        raise ValidationError('Insufficient stock')
    
    variant.current_stock = new_stock
    variant.save(update_fields=['current_stock'])


    movement = InventoryMovement.objects.create(
        variant = variant,
        quantity = quantity,
        movement_type = movement_type,
        note = note,
        created_by = user, 
    )
    return movement