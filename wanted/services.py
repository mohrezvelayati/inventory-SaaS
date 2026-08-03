from django.core.exceptions import ValidationError

from wanted.models import WantedProduct, WantedCustomerRequest



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
    
    wanted_product , created = WantedProduct.objects.get_or_create(
        store=store,
        product=product,
        product_name=product_name,
        size=size,
        defaults={'wanted_count':0}
    )

    wanted_product.wanted_count += 1

    wanted_product.save(
        update_fields=['wanted_count']
    )


    WantedCustomerRequest.objects.create(
        wanted_product=wanted_product,
        customer=customer
    )

    return wanted_product