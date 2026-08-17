from django.test import TestCase
from rest_framework import status

from inventory.models import InventoryMovement
from stores.models import StoreMembership
from tests.factories import (
    authenticated_client,
    create_category,
    create_customer,
    create_product,
    create_sale,
    create_store,
    create_user,
    create_variant,
    create_wanted_product,
)


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.user_a = create_user()
        self.store_a, self.membership_a = create_store(self.user_a)
        self.user_b = create_user()
        self.store_b, self.membership_b = create_store(self.user_b)
        self.client = authenticated_client(self.user_a)

        self.category_b = create_category(self.store_b)
        self.product_b = create_product(
            self.store_b,
            categories=[self.category_b],
        )
        self.variant_b = create_variant(self.product_b, current_stock=10)
        self.customer_b = create_customer(self.store_b)
        self.sale_b = create_sale(
            self.store_b,
            self.membership_b,
            customer=self.customer_b,
        )
        self.wanted_b = create_wanted_product(self.store_b)

    def test_cannot_retrieve_other_store_product(self):
        response = self.client.get(
            f'/api/v1/catalog/products/{self.product_b.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_retrieve_other_store_variant(self):
        response = self.client.get(
            f'/api/v1/catalog/variants/{self.variant_b.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_retrieve_other_store_category(self):
        response = self.client.get(
            f'/api/v1/catalog/categories/{self.category_b.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_retrieve_other_store_customer(self):
        response = self.client.get(
            f'/api/v1/customers/{self.customer_b.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_retrieve_other_store_sale(self):
        response = self.client.get(f'/api/v1/sales/{self.sale_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_complete_other_store_sale(self):
        response = self.client.post(
            f'/api/v1/sales/{self.sale_b.id}/complete/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_cancel_other_store_sale(self):
        response = self.client.post(
            f'/api/v1/sales/{self.sale_b.id}/cancel/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_add_other_store_variant_to_sale(self):
        sale_a = create_sale(self.store_a, self.membership_a)

        response = self.client.post(
            f'/api/v1/sales/{sale_a.id}/items/',
            {'variant': self.variant_b.id, 'quantity': 1, 'discount': 0},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_inventory_movement_for_other_store_variant(self):
        response = self.client.post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': self.variant_b.id,
                'quantity': 1,
                'movement_type': InventoryMovement.MovementType.PURCHASE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inventory_history_does_not_expose_other_store(self):
        InventoryMovement.objects.create(
            variant=self.variant_b,
            quantity=2,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            created_by=self.user_b,
        )

        response = self.client.get('/api/v1/inventory/movements/history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_cannot_retrieve_other_store_wanted_product(self):
        response = self.client.get(f'/api/v1/wanted/{self.wanted_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
