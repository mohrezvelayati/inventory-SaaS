from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class CoreProductWorkflowSmokeTests(TestCase):
    """Exercise the same cross-feature workflow used by the frontend."""

    def setUp(self):
        self.client = APIClient()

    def register_and_login(self, username, phone_number):
        password = 'StrongPass123!'
        register_response = self.client.post(
            '/api/v1/users/register/',
            {
                'username': username,
                'full_name': 'Smoke Test User',
                'phone_number': phone_number,
                'password': password,
            },
            format='json',
        )
        self.assertEqual(
            register_response.status_code,
            status.HTTP_201_CREATED,
        )

        login_response = self.client.post(
            '/api/v1/auth/login/',
            {'username': username, 'password': password},
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        return register_response.data

    def test_registration_to_checkout_dashboard_and_member_invite(self):
        self.register_and_login('smoke-manager', '09120000001')

        store_response = self.client.post(
            '/api/v1/stores/',
            {'name': 'Smoke Store'},
            format='json',
        )
        self.assertEqual(store_response.status_code, status.HTTP_201_CREATED)

        me_response = self.client.get('/api/v1/users/me/')
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            me_response.data['membership']['store']['name'],
            'Smoke Store',
        )

        category_response = self.client.post(
            '/api/v1/catalog/categories/',
            {'name': 'Sneakers'},
            format='json',
        )
        self.assertEqual(
            category_response.status_code,
            status.HTTP_201_CREATED,
        )

        product_response = self.client.post(
            '/api/v1/catalog/products/',
            {
                'name': 'Smoke Sneaker',
                'description': 'End-to-end test product',
                'categories': [category_response.data['id']],
            },
            format='json',
        )
        self.assertEqual(
            product_response.status_code,
            status.HTTP_201_CREATED,
            product_response.data,
        )

        variant_response = self.client.post(
            (
                f"/api/v1/catalog/product/"
                f"{product_response.data['id']}/variants/"
            ),
            {
                'size': '42',
                'purchase_price': 1000,
                'sale_price': 1500,
            },
            format='json',
        )
        self.assertEqual(variant_response.status_code, status.HTTP_201_CREATED)
        variant_id = variant_response.data['id']

        stock_response = self.client.post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': variant_id,
                'quantity': 5,
                'movement_type': 'purchase',
                'note': 'Initial smoke-test stock',
            },
            format='json',
        )
        self.assertEqual(stock_response.status_code, status.HTTP_201_CREATED)

        customer_response = self.client.post(
            '/api/v1/customers/',
            {
                'full_name': 'Smoke Customer',
                'phone_number': '09120000002',
            },
            format='json',
        )
        self.assertEqual(
            customer_response.status_code,
            status.HTTP_201_CREATED,
        )

        sale_response = self.client.post(
            '/api/v1/sales/create/',
            {
                'customer': customer_response.data['id'],
                'channel': 'store',
                'payment_method': 'card',
            },
            format='json',
        )
        self.assertEqual(sale_response.status_code, status.HTTP_201_CREATED)
        sale_id = sale_response.data['id']

        item_response = self.client.post(
            f'/api/v1/sales/{sale_id}/items/',
            {'variant': variant_id, 'quantity': 2, 'discount': 0},
            format='json',
        )
        self.assertEqual(item_response.status_code, status.HTTP_201_CREATED)

        checkout_response = self.client.post(
            f'/api/v1/sales/{sale_id}/complete/',
            format='json',
        )
        self.assertEqual(checkout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            checkout_response.data['message'],
            'Sale completed successfully',
        )

        sale_detail_response = self.client.get(
            f'/api/v1/sales/{sale_id}/'
        )
        self.assertEqual(
            sale_detail_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(sale_detail_response.data['status'], 'completed')
        self.assertEqual(sale_detail_response.data['total_amount'], '3000')

        inventory_response = self.client.get('/api/v1/inventory/')
        self.assertEqual(inventory_response.status_code, status.HTTP_200_OK)
        inventory_item = next(
            item
            for item in inventory_response.data['results']
            if item['id'] == variant_id
        )
        self.assertEqual(inventory_item['current_stock'], 3)

        dashboard_response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['sales']['orders_count'], 1)
        self.assertEqual(dashboard_response.data['sales']['revenue'], 3000)

        wanted_response = self.client.post(
            '/api/v1/wanted/',
            {
                'product': product_response.data['id'],
                'product_name': 'Smoke Sneaker',
                'brand': 'Smoke Brand',
                'size': '43',
                'customer': customer_response.data['id'],
            },
            format='json',
        )
        self.assertEqual(wanted_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(wanted_response.data['wanted_count'], 1)

        employee_client = APIClient()
        employee_response = employee_client.post(
            '/api/v1/users/register/',
            {
                'username': 'smoke-seller',
                'full_name': 'Smoke Seller',
                'phone_number': '09120000003',
                'password': 'StrongPass123!',
            },
            format='json',
        )
        self.assertEqual(employee_response.status_code, status.HTTP_201_CREATED)

        invite_response = self.client.post(
            '/api/v1/stores/members/',
            {'invite_username': 'smoke-seller', 'role': 'seller'},
            format='json',
        )
        self.assertEqual(invite_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(invite_response.data['username'], 'smoke-seller')
