import logging

from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from wanted.models import WantedProduct, WantedCustomerRequest
from dashboard.cache import schedule_dashboard_cache_invalidation


logger = logging.getLogger(__name__)


def _delete_images_after_commit(images):
    stored_files = [
        (image.storage, image.name)
        for image in images
        if image and image.name
    ]
    if not stored_files:
        return

    def delete_files():
        for storage, name in stored_files:
            try:
                storage.delete(name)
            except Exception:
                logger.exception(
                    'Failed to delete wanted request image %s',
                    name,
                )

    transaction.on_commit(delete_files)


@transaction.atomic
def create_wanted(
        *,
        store,
        product=None,
        product_name,
        brand='',
        size,
        customer,
        user=None,
        image=None,
):

    if product is not None and product.store_id != store.id:
        raise ValidationError('Product does not belong to the store')
    if customer is None:
        raise ValidationError('Customer is required')
    if customer.store_id != store.id:
        raise ValidationError('Customer does not belong to the store')
    
    # select_for_update prevents concurrent requests from reading/stale count
    wanted_product, _ = WantedProduct.objects.select_for_update().get_or_create(
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
        image=image,
    )

    schedule_dashboard_cache_invalidation(store.id)

    return wanted_product


@transaction.atomic
def delete_wanted(*, wanted_product):
    store_id = wanted_product.store_id
    images = [
        request.image
        for request in wanted_product.customer_requests.only('image')
        if request.image
    ]

    wanted_product.delete()
    _delete_images_after_commit(images)
    schedule_dashboard_cache_invalidation(store_id)
