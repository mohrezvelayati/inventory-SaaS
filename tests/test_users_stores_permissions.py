from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from stores.models import Permission, StoreMembership
from sales.models import Sale
from tests.factories import (
    authenticated_client,
    create_product,
    create_sale,
    create_store,
    create_user,
    create_variant,
    grant_permission,
)
from users.models import User


class UserApiTests(TestCase):
    def test_registration_hashes_password(self):
        client = APIClient()

        response = client.post(
            '/api/v1/users/register/',
            {
                'username': 'new-user',
                'full_name': 'New User',
                'phone_number': '09123456789',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='new-user')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertNotIn('password', response.data)

    def test_me_requires_authentication(self):
        response = APIClient().get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_authenticated_user_without_membership(self):
        user = create_user()

        response = authenticated_client(user).get('/api/v1/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], user.id)
        self.assertIsNone(response.data['membership'])

    def test_me_returns_manager_store_role_and_effective_permissions(self):
        user = create_user()
        store, membership = create_store(user)

        Permission.objects.get_or_create(
            code='manage_catalog',
            defaults={'name': 'Manage Catalog'},
        )

        response = authenticated_client(user).get('/api/v1/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        membership_data = response.data['membership']

        self.assertEqual(membership_data['id'], membership.id)
        self.assertEqual(
            membership_data['role'],
            StoreMembership.RoleChoices.MANAGER,
        )
        self.assertEqual(membership_data['store']['id'], store.id)
        self.assertEqual(membership_data['store']['name'], store.name)
        self.assertIn(
            'manage_catalog',
            membership_data['permissions'],
        )

    def test_me_returns_only_assigned_permissions_for_seller(self):
        user = create_user()
        store, membership = create_store(
            user,
            role=StoreMembership.RoleChoices.SELLER,
        )

        grant_permission(membership, 'create_sale')

        Permission.objects.get_or_create(
            code='manage_catalog',
            defaults={'name': 'Manage Catalog'},
        )

        response = authenticated_client(user).get('/api/v1/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        membership_data = response.data['membership']

        self.assertEqual(membership_data['store']['id'], store.id)
        self.assertEqual(
            membership_data['role'],
            StoreMembership.RoleChoices.SELLER,
        )
        self.assertEqual(
            membership_data['permissions'],
            ['create_sale'],
        )
        self.assertNotIn(
            'manage_catalog',
            membership_data['permissions'],
        )

    def test_jwt_login_returns_access_and_refresh_tokens(self):
        user = create_user(username='login-user')

        response = APIClient().post(
            '/api/v1/auth/login/',
            {'username': user.username, 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class StoreMembershipTests(TestCase):
    def setUp(self):
        self.manager = create_user()
        self.store, self.manager_membership = create_store(self.manager)
        self.client = authenticated_client(self.manager)

    def test_user_cannot_create_second_store(self):
        response = self.client.post(
            '/api/v1/stores/',
            {'name': 'Second Store'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_database_rejects_second_membership_for_user(self):
        second_store, _ = create_store()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StoreMembership.objects.create(
                    store=second_store,
                    user=self.manager,
                    role=StoreMembership.RoleChoices.SELLER,
                )

    def test_manager_can_add_member_to_own_store(self):
        employee = create_user()

        response = self.client.post(
            '/api/v1/stores/members/',
            {'user': employee.id, 'role': StoreMembership.RoleChoices.SELLER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            StoreMembership.objects.filter(
                store=self.store,
                user=employee,
            ).exists()
        )

    def test_manager_can_invite_member_by_username(self):
        employee = create_user(username='new-seller')

        response = self.client.post(
            '/api/v1/stores/members/',
            {
                'invite_username': employee.username,
                'role': StoreMembership.RoleChoices.SELLER,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], employee.username)
        self.assertEqual(response.data['user_full_name'], employee.full_name)
        self.assertTrue(
            StoreMembership.objects.filter(
                store=self.store,
                user=employee,
            ).exists()
        )

    def test_non_manager_cannot_manage_members_even_with_capability(self):
        seller = create_user()
        seller_membership = StoreMembership.objects.create(
            store=self.store,
            user=seller,
            role=StoreMembership.RoleChoices.SELLER,
        )
        grant_permission(seller_membership, 'manage_members')

        response = authenticated_client(seller).get('/api/v1/stores/members/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_change_own_role(self):
        response = self.client.patch(
            f'/api/v1/stores/members/{self.manager_membership.id}/',
            {'role': StoreMembership.RoleChoices.SELLER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.manager_membership.refresh_from_db()
        self.assertEqual(
            self.manager_membership.role,
            StoreMembership.RoleChoices.MANAGER,
        )

    def test_manager_cannot_access_membership_from_another_store(self):
        _, other_membership = create_store()

        response = self.client.get(
            f'/api/v1/stores/members/{other_membership.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CapabilityPermissionTests(TestCase):
    def setUp(self):
        self.manager = create_user()
        self.store, _ = create_store(self.manager)
        self.seller = create_user()
        self.membership = StoreMembership.objects.create(
            store=self.store,
            user=self.seller,
            role=StoreMembership.RoleChoices.SELLER,
        )
        self.client = authenticated_client(self.seller)

    def test_seller_without_capability_is_denied(self):
        response = self.client.get(
            '/api/v1/catalog/products/?stock_status=in_stock'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_capability_grants_only_expected_access(self):
        grant_permission(self.membership, 'manage_catalog')

        catalog_response = self.client.get(
            '/api/v1/catalog/products/?stock_status=in_stock'
        )
        customer_response = self.client.get('/api/v1/customers/')

        self.assertEqual(catalog_response.status_code, status.HTTP_200_OK)
        self.assertEqual(customer_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_has_implicit_access_without_permission_rows(self):
        manager_client = authenticated_client(self.manager)

        response = manager_client.get(
            '/api/v1/catalog/products/?stock_status=in_stock'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_each_read_capability_grants_its_endpoint(self):
        cases = [
            ('manage_catalog', '/api/v1/catalog/products/?stock_status=in_stock'),
            ('view_inventory', '/api/v1/inventory/'),
            ('view_sales', '/api/v1/sales/'),
            ('manage_customers', '/api/v1/customers/'),
            ('manage_wanted', '/api/v1/wanted/'),
            ('view_dashboard', '/api/v1/dashboard/'),
        ]

        for code, path in cases:
            with self.subTest(code=code):
                seller = create_user()
                membership = StoreMembership.objects.create(
                    store=self.store,
                    user=seller,
                    role=StoreMembership.RoleChoices.SELLER,
                )
                grant_permission(membership, code)

                response = authenticated_client(seller).get(path)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sale_and_manage_inventory_capabilities(self):
        sale_user = create_user()
        sale_membership = StoreMembership.objects.create(
            store=self.store,
            user=sale_user,
            role=StoreMembership.RoleChoices.SELLER,
        )
        grant_permission(sale_membership, 'create_sale')
        sale_response = authenticated_client(sale_user).post(
            '/api/v1/sales/create/',
            {'channel': 'store', 'payment_method': 'cash'},
            format='json',
        )

        inventory_user = create_user()
        inventory_membership = StoreMembership.objects.create(
            store=self.store,
            user=inventory_user,
            role=StoreMembership.RoleChoices.SELLER,
        )
        grant_permission(inventory_membership, 'manage_inventory')
        variant = create_variant(create_product(self.store))
        inventory_response = authenticated_client(inventory_user).post(
            '/api/v1/inventory/movements/create/',
            {
                'variant': variant.id,
                'quantity': 1,
                'movement_type': 'purchase',
            },
            format='json',
        )

        self.assertEqual(sale_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            inventory_response.status_code,
            status.HTTP_201_CREATED,
        )


    def test_deleting_draft_requires_create_sale_capability(self):
        grant_permission(self.membership, 'view_sales')

        sale = create_sale(
            self.store,
            self.membership,
        )

        denied_response = self.client.delete(
            f'/api/v1/sales/{sale.id}/'
        )

        self.assertEqual(
            denied_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            Sale.objects.filter(id=sale.id).exists()
        )

        grant_permission(self.membership, 'create_sale')

        allowed_response = self.client.delete(
            f'/api/v1/sales/{sale.id}/'
        )

        self.assertEqual(
            allowed_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Sale.objects.filter(id=sale.id).exists()
        )
