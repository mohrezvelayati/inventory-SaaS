from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Max, Sum
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import Category, Product, ProductVariant
from customers.models import Customer
from dashboard.services.reports import get_store_report
from inventory.models import InventoryMovement
from sales.models import Sale
from stores.models import Store, StoreInvitation, StoreMembership
from stores.services import get_current_membership
from tests.factories import create_store, create_user
from users.models import User
from wanted.models import WantedProduct


class DemoSeedTests(TestCase):
    def test_command_refuses_to_run_when_demo_mode_is_disabled(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', '--reset')

    @override_settings(DEMO_MODE_ENABLED=True)
    def test_seed_builds_a_complete_and_internally_consistent_tenant(self):
        output = StringIO()
        call_command('seed_demo', '--reset', stdout=output)

        demo_user = User.objects.get(is_demo=True)
        membership = get_current_membership(demo_user)
        store = membership.store

        self.assertEqual(membership.role, StoreMembership.RoleChoices.MANAGER)
        self.assertEqual(StoreMembership.objects.filter(store=store).count(), 3)
        self.assertEqual(Category.objects.filter(store=store).count(), 4)
        self.assertEqual(Product.objects.filter(store=store).count(), 9)
        self.assertEqual(
            ProductVariant.objects.filter(product__store=store).count(),
            24,
        )
        self.assertEqual(Customer.objects.filter(store=store).count(), 12)
        self.assertEqual(Sale.objects.filter(store=store).count(), 16)
        self.assertEqual(
            Sale.objects.filter(
                store=store,
                status=Sale.StatusChoices.COMPLETED,
            ).count(),
            12,
        )
        self.assertEqual(
            Sale.objects.filter(
                store=store,
                status=Sale.StatusChoices.DRAFT,
            ).count(),
            2,
        )
        self.assertEqual(
            Sale.objects.filter(
                store=store,
                status=Sale.StatusChoices.CANCELLED,
            ).count(),
            2,
        )
        self.assertEqual(WantedProduct.objects.filter(store=store).count(), 6)
        self.assertEqual(StoreInvitation.objects.filter(store=store).count(), 2)

        movement_types = set(
            InventoryMovement.objects.filter(
                variant__product__store=store
            ).values_list('movement_type', flat=True)
        )
        self.assertEqual(
            movement_types,
            {'purchase', 'sale', 'adjustment'},
        )
        self.assertTrue(
            InventoryMovement.objects.filter(
                variant__product__store=store,
                movement_type='adjustment',
                quantity__lt=0,
            ).exists()
        )
        self.assertTrue(
            InventoryMovement.objects.filter(
                variant__product__store=store,
                movement_type='adjustment',
                quantity__gt=0,
            ).exists()
        )

        for variant in ProductVariant.objects.filter(product__store=store):
            movement_total = (
                variant.inventory_movements.aggregate(total=Sum('quantity'))['total']
                or 0
            )
            self.assertEqual(variant.current_stock, movement_total)

        report = get_store_report(
            store=store,
            date_from=timezone.localdate() - timedelta(days=29),
            date_to=timezone.localdate(),
        )
        self.assertEqual(report['sales']['orders_count'], 12)
        self.assertGreater(report['sales']['revenue'], 0)
        self.assertGreater(report['sales']['gross_profit'], 0)
        self.assertGreater(report['inventory']['low_stock_count'], 0)
        self.assertGreater(report['inventory']['out_of_stock_count'], 0)
        self.assertIn('products=9', output.getvalue())

    @override_settings(DEMO_MODE_ENABLED=True)
    def test_reset_rebuilds_only_the_demo_tenant(self):
        normal_user = create_user(username='normal-owner', phone_number='09121111111')
        normal_store, _ = create_store(user=normal_user, name='Normal Store')
        call_command('seed_demo', '--reset')
        demo_user = User.objects.get(is_demo=True)
        demo_store = get_current_membership(demo_user).store
        Category.objects.create(store=demo_store, name='Visitor category')

        call_command('seed_demo', '--reset')

        demo_user.refresh_from_db()
        rebuilt_store = get_current_membership(demo_user).store
        self.assertNotEqual(rebuilt_store.pk, demo_store.pk)
        self.assertFalse(
            Category.objects.filter(store=rebuilt_store, name='Visitor category').exists()
        )
        self.assertTrue(Store.objects.filter(pk=normal_store.pk).exists())
        self.assertEqual(get_current_membership(normal_user).store_id, normal_store.pk)


class DemoLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_demo_login_is_hidden_when_disabled(self):
        response = self.client.post('/api/v1/auth/demo/', format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(DEMO_MODE_ENABLED=True)
    def test_demo_login_survives_profile_changes_and_refreshes_dates(self):
        call_command('seed_demo', '--reset')
        demo_user = User.objects.get(is_demo=True)
        store = get_current_membership(demo_user).store
        visitor_category = Category.objects.create(store=store, name='Visitor category')
        shift = timedelta(days=5)
        Sale.objects.filter(
            store=store,
            status=Sale.StatusChoices.COMPLETED,
        ).update(created_at=timezone.now() - shift)
        demo_user.username = 'changed-by-visitor'
        demo_user.save(update_fields=['username'])

        response = self.client.post('/api/v1/auth/demo/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        latest = Sale.objects.filter(
            store=store,
            status=Sale.StatusChoices.COMPLETED,
        ).aggregate(latest=Max('created_at'))['latest']
        self.assertEqual(timezone.localtime(latest).date(), timezone.localdate())
        self.assertTrue(Category.objects.filter(pk=visitor_category.pk).exists())

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        me_response = self.client.get('/api/v1/users/me/')
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertTrue(me_response.data['is_demo'])
        self.assertEqual(me_response.data['username'], 'changed-by-visitor')

    @override_settings(DEMO_MODE_ENABLED=True)
    def test_reset_invalidates_an_existing_demo_access_token(self):
        call_command('seed_demo', '--reset')
        login_response = self.client.post('/api/v1/auth/demo/', format='json')
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        self.assertEqual(
            self.client.get('/api/v1/users/me/').status_code,
            status.HTTP_200_OK,
        )

        call_command('seed_demo', '--reset')

        self.assertEqual(
            self.client.get('/api/v1/users/me/').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
