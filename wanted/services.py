from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from wanted.models import WantedProduct, WantedCustomerRequest


@transaction.atomic
def create_wanted(
        *,
        store,
        product=None,
        product_name,
        brand='',
        size,
        customer=None,
        user=None
):

    if product is not None and product.store_id != store.id:
        raise ValidationError('Product does not belong to the store')
    if customer is not None and customer.store_id != store.id:
        raise ValidationError('Customer does not belong to the store')
    
    wanted_product, created = WantedProduct.objects.get_or_create(
        store=store,
        product_name=product_name,
        size=size,
        defaults={
            'product': product,
            'brand': brand,
            'wanted_count': 0,
        },
    )

    WantedProduct.objects.filter(pk=wanted_product.pk).update(
        wanted_count=F('wanted_count') + 1
    )
    wanted_product.refresh_from_db(fields=['wanted_count'])

    WantedCustomerRequest.objects.create(
        wanted_product=wanted_product,
        customer=customer,
        created_by=user,
    )

    return wanted_product
