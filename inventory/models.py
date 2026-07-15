from django.db import models
from users.models import User


class InventoryMovement(models.Model):

    class MovementType(models.TextChoices):
        PURCHASE = 'purchase', 'Purchase'
        SALE = 'sale', 'Sale'
        ADJUSTMENT = 'adjustment', 'Adjustment'


    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='inventory_movements'
    )

    quantity = models.IntegerField()

    movement_type = models.CharField(max_length=20,choices=MovementType.choices)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return f"{self.variant} : {self.quantity}"