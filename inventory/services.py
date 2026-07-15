from django.db import transaction

from inventory.models import InventoryMovement


@transaction.atomic
def create_inventory_movement(*, variant, quantity, movement_type, user, note=""):

    new_stock = (variant.current_stock + quantity)

    if new_stock < 0:
        raise Exception("Insufficient stock")
    
    variant.current_stock = new_stock
    variant.save()


    movement = InventoryMovement.objects.create(
        variant = variant,
        quantity = quantity,
        movement_type = movement_type,
        note = note,
        created_by = user, 
    )
    return movement