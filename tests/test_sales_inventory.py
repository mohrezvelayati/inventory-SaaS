from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError

from inventory.models import InventoryMovement
from sales.models import Sale, SaleItem
from sales.services import complete_sale
from tests.factories import (
    authenticated_client,
    create_product,
    create_sale,
    create_store,
    create_user,
    create_variant,
)
from users.models import User


class SaleFlowTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, self.membership = create_store(self.user)
        self.client = authenticated_client(self.user)
        self.product = create_product(self.store)
        self.variant = create_variant(
            self.product,
            current_stock=10,
            sale_price=1000,
        )

    def test_complete_sale_decreases_stock_once(self):
        sale = create_sale(self.store, self.membership)
        item_response = self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': self.variant.id, 'quantity': 2, 'discount': 100},
            format='json',
        )

        self.assertEqual(item_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(item_response.data['variant'], self.variant.id)
        self.assertEqual(int(item_response.data['unit_price']), 1000)
        self.assertEqual(int(item_response.data['final_price']), 1900)

        complete_response = self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )

        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        sale.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(sale.status, Sale.StatusChoices.COMPLETED)
        self.assertEqual(self.variant.current_stock, 8)
        self.assertEqual(
            InventoryMovement.objects.get().quantity,
            -2,
        )

        second_response = self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.current_stock, 8)
        self.assertEqual(InventoryMovement.objects.count(), 1)

    def test_cancel_completed_sale_restores_stock_once(self):
        sale = create_sale(self.store, self.membership)
        self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': self.variant.id, 'quantity': 3},
            format='json',
        )
        self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )

        response = self.client.post(
            f'/api/v1/sales/{sale.id}/cancel/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sale.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(sale.status, Sale.StatusChoices.CANCELLED)
        self.assertEqual(self.variant.current_stock, 10)
        self.assertEqual(
            list(
                InventoryMovement.objects.order_by('id').values_list(
                    'quantity',
                    flat=True,
                )
            ),
            [-3, 3],
        )

        second_response = self.client.post(
            f'/api/v1/sales/{sale.id}/cancel/',
            {},
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.current_stock, 10)

    def test_empty_sale_cannot_be_completed(self):
        sale = create_sale(self.store, self.membership)

        response = self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.StatusChoices.DRAFT)

    def test_insufficient_stock_rolls_back_entire_completion(self):
        second_product = create_product(self.store)
        second_variant = create_variant(
            second_product,
            current_stock=1,
            sale_price=500,
        )
        sale = create_sale(self.store, self.membership)
        self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': self.variant.id, 'quantity': 2},
            format='json',
        )
        self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': second_variant.id, 'quantity': 2},
            format='json',
        )

        response = self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        sale.refresh_from_db()
        self.variant.refresh_from_db()
        second_variant.refresh_from_db()
        self.assertEqual(sale.status, Sale.StatusChoices.DRAFT)
        self.assertEqual(self.variant.current_stock, 10)
        self.assertEqual(second_variant.current_stock, 1)
        self.assertEqual(InventoryMovement.objects.count(), 0)

    def test_duplicate_variant_lines_are_validated_as_combined_quantity(self):
        self.variant.current_stock = 5
        self.variant.save(update_fields=['current_stock'])
        sale = create_sale(self.store, self.membership)
        for _ in range(2):
            response = self.client.post(
                f'/api/v1/sales/{sale.id}/items/',
                {'variant': self.variant.id, 'quantity': 3},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            f'/api/v1/sales/{sale.id}/complete/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.current_stock, 5)
        self.assertEqual(InventoryMovement.objects.count(), 0)

    def test_invalid_discounts_are_rejected(self):
        sale = create_sale(self.store, self.membership)

        negative_response = self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': self.variant.id, 'quantity': 1, 'discount': -1},
            format='json',
        )
        excessive_response = self.client.post(
            f'/api/v1/sales/{sale.id}/items/',
            {'variant': self.variant.id, 'quantity': 1, 'discount': 1001},
            format='json',
        )

        self.assertEqual(negative_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(excessive_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SaleItem.objects.count(), 0)

    def test_sale_creation_requires_payment_method(self):
        response = self.client.post(
            '/api/v1/sales/create/',
            {'channel': Sale.ChannelChoices.STORE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sale_filters_are_combined(self):
        matching = create_sale(
            self.store,
            self.membership,
            status=Sale.StatusChoices.COMPLETED,
            channel=Sale.ChannelChoices.INSTAGRAM,
        )
        create_sale(
            self.store,
            self.membership,
            status=Sale.StatusChoices.DRAFT,
            channel=Sale.ChannelChoices.INSTAGRAM,
        )

        response = self.client.get(
            '/api/v1/sales/?status=completed&channel=instagram'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], matching.id)


class InventoryApiTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, _ = create_store(self.user)
        self.client = authenticated_client(self.user)
        self.product = create_product(self.store)
        self.variant = create_variant(self.product, current_stock=1)

    def test_purchase_and_adjustment_update_stock(self):
        purchase_response = self.client.post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': self.variant.id,
                'quantity': 4,
                'movement_type': InventoryMovement.MovementType.PURCHASE,
            },
            format='json',
        )
        adjustment_response = self.client.post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': self.variant.id,
                'quantity': -2,
                'movement_type': InventoryMovement.MovementType.ADJUSTMENT,
            },
            format='json',
        )

        self.assertEqual(purchase_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(adjustment_response.status_code, status.HTTP_201_CREATED)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.current_stock, 3)

    def test_manual_sale_movement_is_rejected(self):
        response = self.client.post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': self.variant.id,
                'quantity': -1,
                'movement_type': InventoryMovement.MovementType.SALE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(InventoryMovement.objects.count(), 0)

    def test_invalid_quantity_rules_are_rejected(self):
        cases = [
            (InventoryMovement.MovementType.PURCHASE, -1),
            (InventoryMovement.MovementType.ADJUSTMENT, 0),
            (InventoryMovement.MovementType.ADJUSTMENT, -2),
        ]

        for movement_type, quantity in cases:
            with self.subTest(movement_type=movement_type, quantity=quantity):
                response = self.client.post(
                    '/api/v1/inventory/movements/create/',
                    {
                        'variant': self.variant.id,
                        'quantity': quantity,
                        'movement_type': movement_type,
                    },
                    format='json',
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_history_has_rich_output_and_filters(self):
        movement = InventoryMovement.objects.create(
            variant=self.variant,
            quantity=2,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            created_by=self.user,
        )
        other_product = create_product(self.store)
        other_variant = create_variant(other_product)
        InventoryMovement.objects.create(
            variant=other_variant,
            quantity=1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )

        response = self.client.get(
            '/api/v1/inventory/movements/history/',
            {
                'product_id': self.product.id,
                'variant_id': self.variant.id,
                'created_by_id': self.user.id,
                'type': InventoryMovement.MovementType.PURCHASE,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        item = response.data['results'][0]
        self.assertEqual(item['id'], movement.id)
        self.assertEqual(item['product_name'], self.product.name)
        self.assertEqual(item['variant_size'], self.variant.size)
        self.assertEqual(item['created_by'], self.user.id)
        self.assertEqual(item['created_by_username'], self.user.username)

    def test_history_rejects_invalid_filters(self):
        invalid_id_response = self.client.get(
            '/api/v1/inventory/movements/history/?product_id=zero'
        )
        invalid_range_response = self.client.get(
            '/api/v1/inventory/movements/history/'
            '?date_from=2026-08-10&date_to=2026-08-01'
        )

        self.assertEqual(
            invalid_id_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            invalid_range_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class ConcurrentCheckoutTests(TransactionTestCase):
    reset_sequences = True

    def test_two_sales_cannot_consume_the_same_final_unit(self):
        user = create_user()
        store, membership = create_store(user)
        product = create_product(store)
        variant = create_variant(product, current_stock=1)
        sales = []
        for _ in range(2):
            sale = create_sale(store, membership)
            SaleItem.objects.create(
                sale=sale,
                variant=variant,
                quantity=1,
                unit_price=variant.sale_price,
                discount=0,
                final_price=variant.sale_price,
            )
            sales.append(sale)

        barrier = Barrier(2)
        outcomes = []

        def checkout(sale_id, user_id):
            close_old_connections()
            try:
                barrier.wait()
                complete_sale(
                    sale=Sale.objects.get(pk=sale_id),
                    user=User.objects.get(pk=user_id),
                )
                outcomes.append('completed')
            except ValidationError:
                outcomes.append('rejected')
            finally:
                close_old_connections()

        threads = [
            Thread(target=checkout, args=(sale.id, user.id))
            for sale in sales
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        variant.refresh_from_db()
        statuses = list(
            Sale.objects.filter(id__in=[sale.id for sale in sales])
            .values_list('status', flat=True)
        )
        self.assertCountEqual(outcomes, ['completed', 'rejected'])
        self.assertEqual(variant.current_stock, 0)
        self.assertEqual(statuses.count(Sale.StatusChoices.COMPLETED), 1)
        self.assertEqual(statuses.count(Sale.StatusChoices.DRAFT), 1)
        self.assertEqual(InventoryMovement.objects.count(), 1)
