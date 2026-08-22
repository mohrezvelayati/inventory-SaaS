from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework import status

from customers.models import Customer
from stores.models import Store
from tests.factories import (
    authenticated_client,
    create_category,
    create_customer,
    create_product,
    create_store,
    create_user,
    create_variant,
)
from users.models import User
from wanted.models import WantedCustomerRequest, WantedProduct
from wanted.services import create_wanted


class CatalogApiTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, _ = create_store(self.user)
        self.client = authenticated_client(self.user)
        self.category = create_category(self.store, name='Shoes')

    def test_product_list_without_stock_filter_returns_all_products(self):
        stocks = [0, 1, 5]
        products = []
        for stock in stocks:
            product = create_product(self.store)
            create_variant(product, current_stock=stock)
            products.append(product)

        response = self.client.get('/api/v1/catalog/products/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertCountEqual(
            [item['id'] for item in response.data['results']],
            [product.id for product in products],
        )

    def test_product_list_returns_variant_details_for_frontend(self):
        product = create_product(self.store, name='Frontend Product')
        variant = create_variant(
            product,
            size='42',
            current_stock=7,
            purchase_price=1000,
            sale_price=1500,
        )

        response = self.client.get('/api/v1/catalog/products/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]
        self.assertEqual(result['id'], product.id)
        self.assertEqual(
            result['variants'],
            [{
                'id': variant.id,
                'size': '42',
                'purchase_price': '1000',
                'sale_price': '1500',
                'current_stock': 7,
            }],
        )

    def test_stock_filters_classify_products(self):
        products = {}
        for label, stock in [('out', 0), ('low', 1), ('in', 5)]:
            product = create_product(self.store, name=label)
            create_variant(product, current_stock=stock)
            products[label] = product

        cases = {
            'out_of_stock': products['out'].id,
            'low_stock': products['low'].id,
            'in_stock': products['in'].id,
        }
        for stock_status, expected_id in cases.items():
            with self.subTest(stock_status=stock_status):
                response = self.client.get(
                    '/api/v1/catalog/products/',
                    {'stock_status': stock_status},
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], expected_id)

    def test_product_search_and_category_filter(self):
        matching = create_product(
            self.store,
            name='Blue Sneaker',
            categories=[self.category],
        )
        create_product(self.store, name='Black Shirt')

        response = self.client.get(
            '/api/v1/catalog/products/',
            {'search': 'sneak', 'category_id': self.category.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], matching.id)

    def test_invalid_stock_status_is_rejected(self):
        response = self.client.get(
            '/api/v1/catalog/products/?stock_status=unknown'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_cannot_reference_category_from_another_store(self):
        other_store, _ = create_store()
        other_category = create_category(other_store)

        response = self.client.post(
            '/api/v1/catalog/products/',
            {
                'name': 'Cross Store Product',
                'description': '',
                'categories': [other_category.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_variant_update_cannot_change_current_stock(self):
        product = create_product(self.store)
        variant = create_variant(product, current_stock=7)

        response = self.client.put(
            f'/api/v1/catalog/variants/{variant.id}/',
            {
                'size': 'Updated',
                'purchase_price': 600,
                'sale_price': 1200,
                'current_stock': 999,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        variant.refresh_from_db()
        self.assertEqual(variant.current_stock, 7)
        self.assertEqual(variant.size, 'Updated')

    def test_variant_list_is_tenant_scoped(self):
        own_product = create_product(self.store)
        own_variant = create_variant(own_product)
        other_store, _ = create_store()
        other_variant = create_variant(create_product(other_store))

        response = self.client.get('/api/v1/catalog/variants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(own_variant.id, ids)
        self.assertNotIn(other_variant.id, ids)


class CustomerApiTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, _ = create_store(self.user)
        self.client = authenticated_client(self.user)

    def test_customer_crud(self):
        create_response = self.client.post(
            '/api/v1/customers/',
            {'full_name': 'Customer', 'phone_number': '09111111111'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        customer_id = create_response.data['id']

        update_response = self.client.patch(
            f'/api/v1/customers/{customer_id}/',
            {'full_name': 'Updated Customer'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['full_name'], 'Updated Customer')

        delete_response = self.client.delete(
            f'/api/v1/customers/{customer_id}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Customer.objects.filter(pk=customer_id).exists())

    def test_phone_is_unique_within_store_but_not_globally(self):
        phone = '09222222222'
        create_customer(self.store, phone_number=phone)

        duplicate_response = self.client.post(
            '/api/v1/customers/',
            {'full_name': 'Duplicate', 'phone_number': phone},
            format='json',
        )
        self.assertEqual(
            duplicate_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        other_store, _ = create_store()
        customer = create_customer(other_store, phone_number=phone)
        self.assertEqual(customer.phone_number, phone)


class WantedApiTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.store, _ = create_store(self.user)
        self.client = authenticated_client(self.user)
        self.product = create_product(self.store)
        self.customer = create_customer(self.store)

    def test_create_wanted_preserves_request_data_and_increments_count(self):
        payload = {
            'product': self.product.id,
            'product_name': 'Rare Shoe',
            'brand': 'Brand X',
            'size': '42',
            'customer': self.customer.id,
        }

        first_response = self.client.post(
            '/api/v1/wanted/',
            payload,
            format='json',
        )
        second_response = self.client.post(
            '/api/v1/wanted/',
            payload,
            format='json',
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        wanted = WantedProduct.objects.get(
            store=self.store,
            product_name='Rare Shoe',
            size='42',
        )
        self.assertEqual(wanted.brand, 'Brand X')
        self.assertEqual(wanted.wanted_count, 2)
        requests = WantedCustomerRequest.objects.filter(wanted_product=wanted)
        self.assertEqual(requests.count(), 2)
        self.assertTrue(requests.filter(customer=self.customer).exists())
        self.assertTrue(requests.filter(created_by=self.user).exists())

    def test_wanted_rejects_other_store_relations(self):
        other_store, _ = create_store()
        other_product = create_product(other_store)
        other_customer = create_customer(other_store)

        product_response = self.client.post(
            '/api/v1/wanted/',
            {
                'product': other_product.id,
                'product_name': 'Other',
                'size': '40',
            },
            format='json',
        )
        customer_response = self.client.post(
            '/api/v1/wanted/',
            {
                'product_name': 'Other',
                'size': '41',
                'customer': other_customer.id,
            },
            format='json',
        )

        self.assertEqual(product_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(customer_response.status_code, status.HTTP_400_BAD_REQUEST)


class WantedConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_requests_do_not_lose_wanted_count(self):
        user = create_user()
        store, _ = create_store(user)
        barrier = Barrier(2)
        outcomes = []

        def record_request(store_id, user_id):
            close_old_connections()
            try:
                barrier.wait()
                create_wanted(
                    store=Store.objects.get(pk=store_id),
                    product_name='Concurrent Product',
                    brand='Brand',
                    size='42',
                    user=User.objects.get(pk=user_id),
                )
                outcomes.append('created')
            finally:
                close_old_connections()

        threads = [
            Thread(target=record_request, args=(store.id, user.id))
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        wanted = WantedProduct.objects.get(
            store=store,
            product_name='Concurrent Product',
            size='42',
        )
        self.assertEqual(outcomes, ['created', 'created'])
        self.assertEqual(wanted.wanted_count, 2)
        self.assertEqual(wanted.customer_requests.count(), 2)
