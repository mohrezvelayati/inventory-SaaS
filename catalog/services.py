import logging

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Category, Product, ProductVariant
from dashboard.cache import schedule_dashboard_cache_invalidation


logger = logging.getLogger(__name__)


VARIANT_SIZE_DUPLICATE_ERROR = "A variant with this size already exists."
VARIANT_MODE_ERROR = (
    "A product cannot have both sized and sizeless variants."
)


def normalize_variant_size(size):
    if size is None:
        return None

    normalized_size = size.strip()
    if not normalized_size:
        raise ValidationError({
            'size': 'Size cannot be blank. Use without_size instead.'
        })
    return normalized_size


def validate_variant_mode(*, product, size, exclude_variant_id=None):
    variants = ProductVariant.objects.filter(product=product)
    if exclude_variant_id is not None:
        variants = variants.exclude(pk=exclude_variant_id)

    if size is None and variants.filter(size__isnull=False).exists():
        raise ValidationError({'size': VARIANT_MODE_ERROR})
    if size is not None and variants.filter(size__isnull=True).exists():
        raise ValidationError({'size': VARIANT_MODE_ERROR})


def create_category(*, store, name):
    """
    Create a new category for a store.
    """
    category = Category.objects.create(store=store, name=name)
    return category


def create_product(*, store, name, description, categories, image=None):
    """
    Create a new product for a store.
    """
    product = Product.objects.create(
        store=store,
        name=name,
        description=description,
        image=image,
    )
    product.category.set(categories)
    return product


def _delete_stored_file_after_commit(file_field):
    if not file_field or not file_field.name:
        return

    storage = file_field.storage
    name = file_field.name

    def delete_file():
        try:
            storage.delete(name)
        except Exception:
            logger.exception('Failed to delete replaced product image %s', name)

    transaction.on_commit(delete_file)


def create_variant(
    *,
    product,
    size,
    purchase_price,
    sale_price,
    invalidate_dashboard=True,
):
    size = normalize_variant_size(size)

    try:
        with transaction.atomic():
            locked_product = Product.objects.select_for_update().get(
                pk=product.pk,
            )
            validate_variant_mode(
                product=locked_product,
                size=size,
            )
            variant = ProductVariant.objects.create(
                product=locked_product,
                size=size,
                purchase_price=purchase_price,
                sale_price=sale_price,
            )
    except IntegrityError as error:
        raise ValidationError({
            'size': VARIANT_SIZE_DUPLICATE_ERROR,
        }) from error

    if invalidate_dashboard:
        schedule_dashboard_cache_invalidation(product.store_id)

    return variant


def update_product(*, product, name, description, categories, image):
    old_image = product.image
    old_image_name = old_image.name if old_image else None

    with transaction.atomic():
        product.name = name
        product.description = description
        product.image = image
        product.save(
            update_fields=['name', 'description', 'image', 'updated_at']
        )
        if categories is not None:
            product.category.set(categories)

        if old_image_name and old_image_name != product.image.name:
            _delete_stored_file_after_commit(old_image)

    schedule_dashboard_cache_invalidation(product.store_id)

    return product


def delete_product(*, product):
    store_id = product.store_id
    image = product.image

    with transaction.atomic():
        product.delete()
        _delete_stored_file_after_commit(image)
        schedule_dashboard_cache_invalidation(store_id)


def update_product_sale_price(*, product, sale_price):
    updated_count = product.variants.update(
        sale_price=sale_price,
        updated_at=timezone.now(),
    )

    if updated_count == 0:
        raise ValidationError({
            'sale_price': 'Product has no variants.'
        })

    return product


def update_variant(*, variant, size, purchase_price, sale_price):
    size = normalize_variant_size(size)

    try:
        with transaction.atomic():
            locked_product = Product.objects.select_for_update().get(
                pk=variant.product_id,
            )
            locked_variant = (
                ProductVariant.objects
                .select_for_update()
                .select_related('product')
                .get(pk=variant.pk, product=locked_product)
            )
            validate_variant_mode(
                product=locked_product,
                size=size,
                exclude_variant_id=locked_variant.id,
            )
            locked_variant.size = size
            locked_variant.purchase_price = purchase_price
            locked_variant.sale_price = sale_price
            locked_variant.save(
                update_fields=[
                    'size',
                    'purchase_price',
                    'sale_price',
                    'updated_at',
                ]
            )
    except IntegrityError as error:
        raise ValidationError({
            'size': VARIANT_SIZE_DUPLICATE_ERROR,
        }) from error

    schedule_dashboard_cache_invalidation(locked_variant.product.store_id)

    return locked_variant
