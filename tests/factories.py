from decimal import Decimal
from itertools import count

from rest_framework.test import APIClient

from catalog.models import Category, Product, ProductVariant
from customers.models import Customer
from sales.models import Sale, SaleItem
from stores.models import (
    MembershipPermission,
    Permission,
    Store,
    StoreMembership,
)
from users.models import User
from wanted.models import WantedProduct


_sequence = count(1)


def create_user(**overrides):
    number = next(_sequence)
    data = {
        'username': f'user{number}',
        'full_name': f'Test User {number}',
        'phone_number': f'09{number:09d}',
        'password': 'StrongPass123!',
    }
    data.update(overrides)
    password = data.pop('password')
    return User.objects.create_user(password=password, **data)


def create_store(user=None, role=StoreMembership.RoleChoices.MANAGER, **overrides):
    user = user or create_user()
    number = next(_sequence)
    store = Store.objects.create(
        name=overrides.get('name', f'Store {number}')
    )
    membership = StoreMembership.objects.create(
        store=store,
        user=user,
        role=role,
    )
    return store, membership


def grant_permission(membership, code):
    permission, _ = Permission.objects.get_or_create(
        code=code,
        defaults={'name': code.replace('_', ' ').title()},
    )
    MembershipPermission.objects.get_or_create(
        membership=membership,
        permission=permission,
    )
    return permission


def create_category(store, **overrides):
    number = next(_sequence)
    return Category.objects.create(
        store=store,
        name=overrides.get('name', f'Category {number}'),
    )


def create_product(store, categories=None, **overrides):
    number = next(_sequence)
    product = Product.objects.create(
        store=store,
        name=overrides.get('name', f'Product {number}'),
        description=overrides.get('description', ''),
    )
    if categories:
        product.category.set(categories)
    return product


def create_variant(product, **overrides):
    number = next(_sequence)
    return ProductVariant.objects.create(
        product=product,
        size=overrides.get('size', f'Size {number}'),
        purchase_price=overrides.get('purchase_price', Decimal('500')),
        sale_price=overrides.get('sale_price', Decimal('1000')),
        current_stock=overrides.get('current_stock', 0),
    )


def create_customer(store, **overrides):
    number = next(_sequence)
    return Customer.objects.create(
        store=store,
        full_name=overrides.get('full_name', f'Customer {number}'),
        phone_number=overrides.get('phone_number', f'09{number:09d}'),
    )


def create_sale(store, seller, **overrides):
    return Sale.objects.create(
        store=store,
        seller=seller,
        customer=overrides.get('customer'),
        channel=overrides.get('channel', Sale.ChannelChoices.STORE),
        payment_method=overrides.get(
            'payment_method',
            Sale.PaymentChoices.CASH,
        ),
        status=overrides.get('status', Sale.StatusChoices.DRAFT),
        total_amount=overrides.get('total_amount', Decimal('0')),
    )


def create_sale_item(sale, variant, **overrides):
    quantity = overrides.get('quantity', 1)
    unit_price = overrides.get('unit_price', variant.sale_price)
    discount = overrides.get('discount', Decimal('0'))
    return SaleItem.objects.create(
        sale=sale,
        variant=variant,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        final_price=overrides.get(
            'final_price',
            unit_price * quantity - discount,
        ),
    )


def create_wanted_product(store, **overrides):
    number = next(_sequence)
    return WantedProduct.objects.create(
        store=store,
        product=overrides.get('product'),
        product_name=overrides.get('product_name', f'Wanted {number}'),
        brand=overrides.get('brand', ''),
        size=overrides.get('size', f'Size {number}'),
        wanted_count=overrides.get('wanted_count', 1),
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
