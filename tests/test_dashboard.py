from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from dashboard.services.inventory import get_inventory_overview
from dashboard.services.sales import get_sales_overview
from sales.models import Sale
from stores.models import StoreMembership
from tests.factories import (
    authenticated_client,
    create_product,
    create_sale,
    create_sale_item,
    create_store,
    create_user,
    create_variant,
    grant_permission,
)


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(self.user)

    def test_multi_item_sale_is_not_double_counted(self):
        product = create_product(self.store)
        first_variant = create_variant(product, sale_price=1000)
        second_variant = create_variant(product, sale_price=2000)
        sale = create_sale(
            self.store,
            self.membership,
            status=Sale.StatusChoices.COMPLETED,
            total_amount=Decimal('2850'),
        )
        create_sale_item(
            sale,
            first_variant,
            discount=Decimal('50'),
            final_price=Decimal('950'),
        )
        create_sale_item(
            sale,
            second_variant,
            discount=Decimal('100'),
            final_price=Decimal('1900'),
        )
        today = timezone.localdate()

        result = get_sales_overview(
            store=self.store,
            date_from=today,
            date_to=today,
        )

        self.assertEqual(result['orders_count'], 1)
        self.assertEqual(result['revenue'], Decimal('2850'))
        self.assertEqual(result['discount'], Decimal('150'))

    def test_empty_inventory_returns_zero_values(self):
        result = get_inventory_overview(store=self.store)

        self.assertEqual(result['total_variants'], 0)
        self.assertEqual(result['total_stock'], 0)


class DashboardApiTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(self.user)
        self.client = authenticated_client(self.user)

    def test_dashboard_response_matches_documented_contract(self):
        response = self.client.get('/api/v1/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {'sales', 'inventory', 'low_stock', 'products', 'wanted'},
        )
        self.assertEqual(response.data['inventory']['total_stock'], 0)

    def test_dashboard_rejects_invalid_reversed_and_large_date_ranges(self):
        invalid_response = self.client.get(
            '/api/v1/dashboard/?date_from=invalid'
        )
        reversed_response = self.client.get(
            '/api/v1/dashboard/?date_from=2026-08-10&date_to=2026-08-01'
        )
        large_response = self.client.get(
            '/api/v1/dashboard/?date_from=2026-01-01&date_to=2026-08-01'
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reversed_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(large_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_requires_dashboard_capability(self):
        seller = create_user()
        seller_membership = StoreMembership.objects.create(
            store=self.store,
            user=seller,
            role=StoreMembership.RoleChoices.SELLER,
        )
        seller_client = authenticated_client(seller)

        denied = seller_client.get('/api/v1/dashboard/')
        grant_permission(seller_membership, 'view_dashboard')
        allowed = seller_client.get('/api/v1/dashboard/')

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
