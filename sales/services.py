from django.db import transaction
from django.db.models import Sum

from sales.models import Sale, SaleItem
from inventory.services import create_inventory_movement
from django.core.exceptions import ValidationError



### Create empty sale (Draft) ###
@transaction.atomic
def create_sale(*, store, seller, customer=None, channel, payment_method=None):


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


### Add item to sale ###
@transaction.atomic
def add_sale_item(*, sale, variant, quantity, discount=0):
    if sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError(
           " امکان اصلاح فروش تکمیل‌شده وجود ندارد."
        )
    

    if quantity <= 0:
        raise ValidationError(
            "مقدار باید بزرگتر از صفر باشد."
        )
    
    # Get the current selling price
    unit_price = variant.sale_price


    line_total = (unit_price * quantity) - discount


    items = SaleItem.objects.create(
        sale=sale,
        variant=variant,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        final_price=line_total
    )


    update_sale_total(sale)

    return sale



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
def validate_sale_stock(sale):
    """
    Check if all sale items have enough stock
    """
    errors = []

    for item in sale.items.select_related('variant'):
        available_stock = item.variant.current_stock
        if available_stock < item.quantity:
            errors.append(
                {
                    "variant": item.variant.id,
                    "product": item.variant.product.name,
                    "requested": item.quantity,
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
    if sale.status != Sale.StatusChoices.DRAFT :
        raise ValidationError(
            "فقط فروش درحال تکمیل می‌تواند تکمیل شود"
        )
    items = sale.items.all()


    if not items.exists():
        raise ValidationError(
            "نمی‌توان فروش خالی را تکمیل کرد"
        )
    
    validate_sale_stock(
        sale
    )

    # کاهش موجودی
    for item in items:
        create_inventory_movement(
            variant=item.variant,
            quantity=item.quantity,
            movement_type='sale',
            user=user,
            note=f"Sale #{sale.id}"
        )

    sale.status = Sale.StatusChoices.COMPLETED

    sale.save(
        update_fields = ['status']
    )

    return sale



### Cancel Sale ###
@transaction.atomic
def cansel_sale(*, sale):
    if sale.status != Sale.StatusChoices.DRAFT:
        raise ValidationError(
            "فقط فروش درحال تکمیل می‌تواند کنسل شود"
        )
    sale.status = Sale.StatusChoices.CANCELLED


    sale.save(
        update_fields = ['status']
    )

    return sale