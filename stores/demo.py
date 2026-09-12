from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from catalog.services import create_category, create_product, create_variant
from customers.services import create_customer
from inventory.models import InventoryMovement
from inventory.services import create_inventory_movement
from sales.models import Sale
from sales.services import add_sale_item, cancel_sale, complete_sale, create_sale
from stores.models import Store, StoreMembership
from stores.services import (
    NoMembershipError,
    create_store_invitation,
    create_store_membership,
    create_store_with_membership,
    get_current_membership,
)
from users.models import User
from wanted.services import create_wanted


DEMO_USERNAME = 'portfolio_demo'


def _unique_username(base, *, exclude_user_id=None):
    candidate = base
    suffix = 1
    queryset = User.objects.exclude(pk=exclude_user_id)
    while queryset.filter(username=candidate).exists():
        candidate = f'{base}_{suffix}'
        suffix += 1
    return candidate


def _unique_phone(start, *, exclude_user_id=None):
    queryset = User.objects.exclude(pk=exclude_user_id)
    number = start
    while True:
        candidate = f'09{number:09d}'
        if not queryset.filter(phone_number=candidate).exists():
            return candidate
        number += 1


def _get_or_create_demo_user():
    try:
        user = User.objects.select_for_update().get(is_demo=True)
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=_unique_username(DEMO_USERNAME),
            full_name='مدیر فروشگاه دمو',
            phone_number=_unique_phone(1),
            password=None,
            is_demo=True,
        )

    user.username = _unique_username(DEMO_USERNAME, exclude_user_id=user.pk)
    user.full_name = 'مدیر فروشگاه دمو'
    user.phone_number = _unique_phone(1, exclude_user_id=user.pk)
    user.is_active = True
    user.is_staff = False
    user.is_superuser = False
    user.set_unusable_password()
    user.save(
        update_fields=[
            'username',
            'full_name',
            'phone_number',
            'is_active',
            'is_staff',
            'is_superuser',
            'password',
        ]
    )
    return user


def _prepare_employee(*, username, full_name, phone_seed):
    reusable = list(
        User.objects.filter(
            Q(username=username) | Q(phone_number=f'09{phone_seed:09d}')
        )
    )
    user = reusable[0] if len(reusable) == 1 and not reusable[0].memberships.exists() else None
    if user is None:
        user = User()

    user.username = _unique_username(username, exclude_user_id=user.pk)
    user.full_name = full_name
    user.phone_number = _unique_phone(phone_seed, exclude_user_id=user.pk)
    user.is_active = True
    user.set_unusable_password()
    user.save()
    return user


def _set_sale_date(*, sale, created_at):
    Sale.objects.filter(pk=sale.pk).update(created_at=created_at)
    InventoryMovement.objects.filter(
        Q(note=f'Sale #{sale.pk}')
        | Q(note=f'Cancellation of Sale #{sale.pk}')
    ).update(created_at=created_at)


@transaction.atomic
def refresh_demo_timeline(*, user):
    """Move the demo sales timeline forward without removing visitor changes."""

    if not user.is_demo:
        return 0

    membership = get_current_membership(user)
    Store.objects.select_for_update().get(pk=membership.store_id)
    latest = (
        Sale.objects.filter(
            store_id=membership.store_id,
            status=Sale.StatusChoices.COMPLETED,
        ).aggregate(latest=Max('created_at'))['latest']
    )
    if latest is None:
        return 0

    latest_date = timezone.localtime(latest).date()
    days = (timezone.localdate() - latest_date).days
    if days == 0:
        return 0

    shift = timedelta(days=days)
    Sale.objects.filter(
        store_id=membership.store_id,
        status__in=[
            Sale.StatusChoices.COMPLETED,
            Sale.StatusChoices.CANCELLED,
        ],
    ).update(created_at=F('created_at') + shift)
    InventoryMovement.objects.filter(
        Q(movement_type=InventoryMovement.MovementType.SALE)
        | Q(note__startswith='Cancellation of Sale #'),
        variant__product__store_id=membership.store_id,
    ).update(created_at=F('created_at') + shift)
    return days


@transaction.atomic
def reset_demo_data():
    """Rebuild the single public demo tenant through normal domain services."""

    demo_user = _get_or_create_demo_user()
    try:
        old_membership = get_current_membership(demo_user)
    except NoMembershipError:
        old_membership = None

    if old_membership is not None:
        old_store = Store.objects.select_for_update().get(pk=old_membership.store_id)
        # Sale protects its seller membership and SaleItem protects its variant.
        # A demo reset is the one explicit workflow allowed to remove these
        # synthetic audit records before cascading the tenant itself.
        Sale.objects.filter(store=old_store).delete()
        old_store.delete()

    store = create_store_with_membership(
        user=demo_user,
        name='فروشگاه دمو انبارینو',
    )
    manager = get_current_membership(demo_user)

    seller_user = _prepare_employee(
        username='demo_seller',
        full_name='سارا احمدی',
        phone_seed=2,
    )
    admin_user = _prepare_employee(
        username='demo_admin',
        full_name='امیر رضایی',
        phone_seed=3,
    )
    seller = create_store_membership(
        store=store,
        user=seller_user,
        role=StoreMembership.RoleChoices.SELLER,
    )
    admin = create_store_membership(
        store=store,
        user=admin_user,
        role=StoreMembership.RoleChoices.ADMIN,
    )

    categories = {
        'casual': create_category(store=store, name='کتانی روزمره'),
        'running': create_category(store=store, name='کفش ورزشی'),
        'clothing': create_category(store=store, name='پوشاک'),
        'accessory': create_category(store=store, name='اکسسوری'),
    }

    product_specs = [
        ('air_force', 'کتانی نایکی ایر فورس ۱', 'کتانی سفید روزمره و پرفروش', ['casual'], [('40', 2800000, 3950000), ('41', 2800000, 3950000), ('42', 2850000, 4050000)]),
        ('samba', 'کتانی آدیداس سامبا', 'مدل کلاسیک مناسب استایل روزمره', ['casual'], [('38', 3100000, 4450000), ('39', 3100000, 4450000), ('40', 3150000, 4550000)]),
        ('nb530', 'کتانی نیوبالانس ۵۳۰', 'کتانی سبک با ترکیب رنگ نقره‌ای', ['casual'], [('39', 3500000, 4950000), ('40', 3500000, 4950000), ('41', 3550000, 5050000)]),
        ('pegasus', 'کفش رانینگ نایکی پگاسوس', 'مناسب دویدن و تمرین روزانه', ['running'], [('41', 4200000, 5900000), ('42', 4200000, 5900000), ('43', 4250000, 6050000)]),
        ('hoodie', 'هودی اورسایز', 'هودی دورس سه‌نخ مناسب فصل سرد', ['clothing'], [('M', 850000, 1290000), ('L', 850000, 1290000), ('XL', 890000, 1350000)]),
        ('tshirt', 'تیشرت بیسیک پنبه‌ای', 'تیشرت ساده با پارچه پنبه‌ای', ['clothing'], [('S', 390000, 620000), ('M', 390000, 620000), ('L', 410000, 650000)]),
        ('bag', 'کیف کمری اسپرت', 'کیف سبک مناسب استفاده روزانه', ['accessory'], [('کوچک', 430000, 690000), ('بزرگ', 510000, 790000)]),
        ('jeans', 'شلوار جین راسته', 'شلوار جین آبی با برش راسته', ['clothing'], [('30', 920000, 1390000), ('32', 920000, 1390000), ('34', 950000, 1450000), ('36', 950000, 1450000)]),
        ('future', 'محصول در انتظار تأمین', 'محصول تازه ثبت‌شده و بدون سایز', ['accessory'], []),
    ]

    products = {}
    variants = {}
    purchase_movement_ids = []
    for product_key, name, description, category_keys, variant_specs in product_specs:
        product = create_product(
            store=store,
            name=name,
            description=description,
            categories=[categories[key] for key in category_keys],
        )
        products[product_key] = product
        for size, purchase_price, sale_price in variant_specs:
            variant = create_variant(
                product=product,
                size=size,
                purchase_price=Decimal(purchase_price),
                sale_price=Decimal(sale_price),
            )
            variants[f'{product_key}:{size}'] = variant
            movement = create_inventory_movement(
                store=store,
                variant=variant,
                quantity=10,
                movement_type=InventoryMovement.MovementType.PURCHASE,
                user=demo_user,
                note='موجودی اولیه دموی فروشگاه',
            )
            purchase_movement_ids.append(movement.pk)

    now = timezone.now()
    InventoryMovement.objects.filter(pk__in=purchase_movement_ids).update(
        created_at=now - timedelta(days=35)
    )

    customer_specs = [
        ('علی محمدی', 'male', 27), ('مریم کریمی', 'female', 24),
        ('رضا حیدری', 'male', 32), ('نگار اکبری', 'female', 29),
        ('سامان شریفی', 'male', 21), ('الهام مرادی', 'female', 35),
        ('کیان نادری', 'male', 26), ('ترانه یوسفی', 'female', 31),
        ('آرش کاظمی', 'male', 38), ('هستی صالحی', 'female', 22),
        ('محمد پارسا', 'male', 44), ('پریسا زمانی', 'female', 28),
    ]
    customers = []
    for index, (full_name, gender, age) in enumerate(customer_specs, start=101):
        customers.append(create_customer(
            store=store,
            full_name=full_name,
            phone_number=f'09000000{index:03d}',
            gender=gender,
            age=age,
        ))

    sale_specs = [
        (29, seller, 0, 'store', 'card', [('air_force:42', 2, 100000), ('hoodie:L', 1, 0)]),
        (25, admin, 1, 'instagram', 'online', [('samba:39', 1, 0)]),
        (21, seller, 2, 'website', 'online', [('nb530:40', 2, 150000)]),
        (17, manager, 3, 'referral', 'cash', [('pegasus:42', 1, 200000), ('bag:بزرگ', 1, 0)]),
        (14, seller, 4, 'other', 'card', [('tshirt:M', 2, 50000)]),
        (11, admin, 5, 'store', 'cash', [('jeans:32', 1, 0)]),
        (8, seller, 6, 'instagram', 'online', [('air_force:41', 1, 0)]),
        (6, manager, 7, 'website', 'online', [('samba:40', 2, 100000)]),
        (4, seller, 8, 'store', 'card', [('nb530:39', 1, 0), ('bag:کوچک', 1, 0)]),
        (2, admin, 9, 'referral', 'cash', [('pegasus:43', 2, 250000)]),
        (1, seller, 10, 'instagram', 'online', [('hoodie:M', 1, 0), ('tshirt:L', 1, 30000)]),
        (0, manager, 11, 'store', 'card', [('air_force:40', 1, 0), ('jeans:30', 1, 50000)]),
    ]

    for offset, sale_seller, customer_index, channel, payment, item_specs in sale_specs:
        sale = create_sale(
            store=store,
            seller=sale_seller,
            customer=customers[customer_index],
            channel=channel,
            payment_method=payment,
        )
        for variant_key, quantity, discount in item_specs:
            add_sale_item(
                sale=sale,
                variant=variants[variant_key],
                quantity=quantity,
                discount=Decimal(discount),
            )
        complete_sale(sale=sale, user=sale_seller.user)
        _set_sale_date(sale=sale, created_at=now - timedelta(days=offset))

    cancelled_specs = [
        (9, seller, customers[2], 'instagram', 'online', 'samba:38', 2),
        (3, admin, customers[5], 'store', 'card', 'pegasus:41', 1),
    ]
    for offset, sale_seller, customer, channel, payment, variant_key, quantity in cancelled_specs:
        sale = create_sale(
            store=store,
            seller=sale_seller,
            customer=customer,
            channel=channel,
            payment_method=payment,
        )
        add_sale_item(sale=sale, variant=variants[variant_key], quantity=quantity)
        complete_sale(sale=sale, user=sale_seller.user)
        cancel_sale(sale=sale, user=demo_user)
        _set_sale_date(sale=sale, created_at=now - timedelta(days=offset))

    draft_specs = [
        (seller, customers[4], 'website', 'online', 'nb530:41', 1),
        (admin, customers[7], 'instagram', 'online', 'hoodie:XL', 1),
    ]
    for sale_seller, customer, channel, payment, variant_key, quantity in draft_specs:
        sale = create_sale(
            store=store,
            seller=sale_seller,
            customer=customer,
            channel=channel,
            payment_method=payment,
        )
        add_sale_item(sale=sale, variant=variants[variant_key], quantity=quantity)

    target_stocks = {
        'samba:38': 0,
        'nb530:41': 1,
        'hoodie:XL': 2,
    }
    for variant_key, target_stock in target_stocks.items():
        variant = variants[variant_key]
        variant.refresh_from_db(fields=['current_stock'])
        create_inventory_movement(
            store=store,
            variant=variant,
            quantity=target_stock - variant.current_stock,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            user=demo_user,
            note='اصلاح موجودی برای نمایش وضعیت هشدار',
        )

    bag = variants['bag:کوچک']
    create_inventory_movement(
        store=store,
        variant=bag,
        quantity=2,
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        user=demo_user,
        note='اصلاح مثبت موجودی پس از شمارش انبار',
    )

    wanted_specs = [
        (products['air_force'], 'کتانی نایکی ایر فورس ۱', 'Nike', '43', 7),
        (None, 'کتانی آدیداس گزل', 'Adidas', '40', 5),
        (products['nb530'], 'کتانی نیوبالانس ۵۳۰', 'New Balance', '42', 4),
        (None, 'کفش رانینگ هوکا', 'Hoka', '41', 3),
        (products['hoodie'], 'هودی اورسایز', '', 'XXL', 2),
        (None, 'کلاه کپ مشکی', '', 'تک‌سایز', 1),
    ]
    for product, product_name, brand, size, count in wanted_specs:
        for index in range(count):
            create_wanted(
                store=store,
                product=product,
                product_name=product_name,
                brand=brand,
                size=size,
                customer=customers[index % len(customers)] if index % 2 == 0 else None,
                user=demo_user if index % 3 == 0 else seller_user,
            )

    create_store_invitation(
        actor_membership=manager,
        phone_number='09000000201',
        role=StoreMembership.RoleChoices.SELLER,
    )
    create_store_invitation(
        actor_membership=manager,
        phone_number='09000000202',
        role=StoreMembership.RoleChoices.ADMIN,
    )

    return {
        'user': demo_user,
        'store': store,
        'products': len(products),
        'variants': len(variants),
        'customers': len(customers),
        'sales': 16,
        'wanted': len(wanted_specs),
    }
