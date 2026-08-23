from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework import status

from customers.models import Customer
from sales.models import Sale, SaleItem
from stores.models import Store, StoreMembership
from tests.factories import (
    authenticated_client,
    create_category,
    create_customer,
    create_product,
    create_sale,
    create_sale_item,
    create_store,
    create_user,
    create_variant,
    create_wanted_product,
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

    def test_product_filter_by_variant_size(self):
        size_40 = create_product(self.store, name='Sneaker 40')
        create_variant(size_40, size='40', current_stock=2)
        size_41 = create_product(self.store, name='Sneaker 41')
        create_variant(size_41, size='41', current_stock=2)
        create_product(self.store, name='No Variant')

        response = self.client.get(
            '/api/v1/catalog/products/',
            {'size': '40'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], size_40.id)

        empty_response = self.client.get(
            '/api/v1/catalog/products/',
            {'size': '99'},
        )
        self.assertEqual(empty_response.data['count'], 0)

    def test_invalid_stock_status_is_rejected(self):
        response = self.client.get(
            '/api/v1/catalog/products/?stock_status=unknown'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_ordering_is_whitelisted(self):
        first = create_product(self.store, name='Zulu')
        second = create_product(self.store, name='Alpha')

        response = self.client.get('/api/v1/catalog/products/', {'ordering': 'name'})
        invalid_response = self.client.get('/api/v1/catalog/products/', {'ordering': 'price'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertLess(ids.index(second.id), ids.index(first.id))
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

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
            {
                'full_name': 'Customer',
                'phone_number': '09111111111',
                'gender': 'male',
                'age': 30,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        customer_id = create_response.data['id']
        self.assertEqual(create_response.data['gender'], 'male')
        self.assertEqual(create_response.data['age'], 30)

        update_response = self.client.patch(
            f'/api/v1/customers/{customer_id}/',
            {'full_name': 'Updated Customer', 'gender': 'female', 'age': 31},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['full_name'], 'Updated Customer')
        self.assertEqual(update_response.data['gender'], 'female')
        self.assertEqual(update_response.data['age'], 31)

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
            {'full_name': 'Duplicate', 'phone_number': phone, 'gender': 'female'},
            format='json',
        )
        self.assertEqual(
            duplicate_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        other_store, _ = create_store()
        customer = create_customer(other_store, phone_number=phone)
        self.assertEqual(customer.phone_number, phone)

    def test_customer_search_matches_name_or_phone(self):
        matching = create_customer(
            self.store,
            full_name='Sara Ahmadi',
            phone_number='09123456789',
        )
        create_customer(self.store, full_name='Reza Karimi')

        for search in ['sara', '4567']:
            with self.subTest(search=search):
                response = self.client.get('/api/v1/customers/', {'search': search})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], matching.id)

    def test_customer_filters_gender_and_age(self):
        create_customer(self.store, full_name='Ali', gender='male', age=30)
        create_customer(self.store, full_name='Sara', gender='female', age=30)
        create_customer(self.store, full_name='Reza', gender='male', age=40)
        create_customer(self.store, full_name='Nina', gender='female', age=25)

        male = self.client.get('/api/v1/customers/', {'gender': 'male'})
        self.assertEqual(male.status_code, status.HTTP_200_OK)
        self.assertEqual(male.data['count'], 2)

        age30 = self.client.get(
            '/api/v1/customers/',
            {'age_min': 30, 'age_max': 30},
        )
        self.assertEqual(age30.status_code, status.HTTP_200_OK)
        self.assertEqual(age30.data['count'], 2)

        combined = self.client.get(
            '/api/v1/customers/',
            {'gender': 'female', 'age_min': 25, 'age_max': 25},
        )
        self.assertEqual(combined.status_code, status.HTTP_200_OK)
        self.assertEqual(combined.data['count'], 1)
        self.assertEqual(combined.data['results'][0]['full_name'], 'Nina')

        bad_gender = self.client.get('/api/v1/customers/', {'gender': 'unknown'})
        self.assertEqual(bad_gender.status_code, status.HTTP_400_BAD_REQUEST)

        open_ended = self.client.get('/api/v1/customers/', {'age_min': 31})
        self.assertEqual(open_ended.status_code, status.HTTP_200_OK)
        self.assertEqual(open_ended.data['count'], 1)
        self.assertEqual(open_ended.data['results'][0]['full_name'], 'Reza')

        bad_age_min = self.client.get('/api/v1/customers/', {'age_min': 'abc'})
        self.assertEqual(bad_age_min.status_code, status.HTTP_400_BAD_REQUEST)

        bad_range = self.client.get(
            '/api/v1/customers/',
            {'age_min': 30, 'age_max': 20},
        )
        self.assertEqual(bad_range.status_code, status.HTTP_400_BAD_REQUEST)

    def test_total_items_purchased_counts_only_completed_sale_quantities(self):
        customer = create_customer(
            self.store,
            full_name='Buyer',
            phone_number='09333333333',
            gender='male',
            age=35,
        )
        product = create_product(self.store)
        variant = create_variant(product, current_stock=10)
        # Re-fetch the seller membership from the store created in setUp.
        seller = StoreMembership.objects.get(store=self.store)

        # Two completed sales: quantities 2 and 3 -> total 5.
        for qty in (2, 3):
            sale = create_sale(
                self.store,
                seller,
                customer=customer,
                status=Sale.StatusChoices.COMPLETED,
            )
            create_sale_item(sale, variant, quantity=qty)

        # A draft sale must NOT count toward the total.
        draft = create_sale(
            self.store,
            seller,
            customer=customer,
            status=Sale.StatusChoices.DRAFT,
        )
        create_sale_item(draft, variant, quantity=100)

        response = self.client.get('/api/v1/customers/', {'search': 'Buyer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['total_items_purchased'],
            5,
        )


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

    def test_wanted_can_be_updated_and_deleted(self):
        wanted = create_wanted_product(
            self.store,
            product_name='Old Name',
            brand='Old Brand',
            size='40',
        )

        update_response = self.client.patch(
            f'/api/v1/wanted/{wanted.id}/',
            {'product_name': 'New Name', 'brand': 'New Brand', 'size': '41'},
            format='json',
        )
        delete_response = self.client.delete(f'/api/v1/wanted/{wanted.id}/')

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['product_name'], 'New Name')
        self.assertEqual(update_response.data['brand'], 'New Brand')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WantedProduct.objects.filter(id=wanted.id).exists())

    def test_wanted_search_matches_name_brand_or_size(self):
        matching = create_wanted_product(
            self.store,
            product_name='Air Zoom',
            brand='Nike',
            size='43',
        )
        create_wanted_product(self.store, product_name='Classic Shirt')

        for search in ['zoom', 'nike', '43']:
            with self.subTest(search=search):
                response = self.client.get('/api/v1/wanted/', {'search': search})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], matching.id)

    def test_wanted_filters_are_combined_and_validated(self):
        today = timezone.localdate().isoformat()
        matching = create_wanted_product(
            self.store,
            product=self.product,
            product_name='Popular Shoe',
            size='44',
            wanted_count=5,
        )
        create_wanted_product(self.store, wanted_count=1)

        response = self.client.get('/api/v1/wanted/', {
            'min_count': 5,
            'product_id': self.product.id,
            'date_from': today,
            'date_to': today,
        })
        invalid_count = self.client.get('/api/v1/wanted/', {'min_count': 0})
        invalid_range = self.client.get('/api/v1/wanted/', {
            'date_from': '2026-08-22',
            'date_to': '2026-08-21',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], matching.id)
        self.assertEqual(invalid_count.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_range.status_code, status.HTTP_400_BAD_REQUEST)


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
