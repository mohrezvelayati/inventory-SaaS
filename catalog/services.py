from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Category, Product, ProductVariant


VARIANT_SIZE_DUPLICATE_ERROR = "A variant with this size already exists."


def create_category(*, store, name):
    """
    Create a new category for a store.
    """
    category = Category.objects.create(store=store, name=name)
    return category


def create_product(*, store, name, description, categories):
    """
    Create a new product for a store.
    """
    product = Product.objects.create(store=store, name=name, description=description)
    product.category.set(categories)
    return product


def create_variant(*, product, size, purchase_price, sale_price):
    try:
        with transaction.atomic():
            return ProductVariant.objects.create(
                product=product,
                size=size,
                purchase_price=purchase_price,
                sale_price=sale_price
            )
    except IntegrityError as error:
        raise ValidationError({
            'size': VARIANT_SIZE_DUPLICATE_ERROR,
        }) from error


def update_product(*, product, name, description, categories):
    product.name = name
    product.description = description
    product.save(update_fields=['name', 'description', 'updated_at'])
    if categories is not None:
        product.category.set(categories)
    return product


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
    variant.size = size
    variant.purchase_price = purchase_price
    variant.sale_price = sale_price
    try:
        with transaction.atomic():
            variant.save(
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
    return variant
