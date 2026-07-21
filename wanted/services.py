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