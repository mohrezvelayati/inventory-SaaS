import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from stores.models import (
    MembershipPermission,
    Permission,
    StoreInvitation,
    StoreMembership,
)
from stores.services import InvitationError, accept_store_invitation
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

    def test_user_can_update_only_their_profile_fields(self):
        user = create_user(username='profile-user')
        client = authenticated_client(user)

        response = client.patch(
            '/api/v1/users/me/',
            {
                'username': 'updated-user',
                'full_name': 'Updated Name',
                'phone_number': '09120001122',
                'membership': {'role': 'manager'},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.username, 'updated-user')
        self.assertEqual(user.full_name, 'Updated Name')
        self.assertEqual(user.phone_number, '09120001122')
        self.assertIsNone(response.data['membership'])


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

    def test_manager_can_view_and_rename_current_store(self):
        get_response = self.client.get('/api/v1/stores/current/')
        update_response = self.client.patch(
            '/api/v1/stores/current/',
            {'name': 'Renamed Store'},
            format='json',
        )

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['id'], self.store.id)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, 'Renamed Store')

    def test_non_manager_cannot_update_store_settings(self):
        seller = create_user()
        StoreMembership.objects.create(
            store=self.store,
            user=seller,
            role=StoreMembership.RoleChoices.SELLER,
        )

        response = authenticated_client(seller).patch(
            '/api/v1/stores/current/',
            {'name': 'Unauthorized Rename'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.store.refresh_from_db()
        self.assertNotEqual(self.store.name, 'Unauthorized Rename')

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


class StoreInvitationApiTests(TestCase):
    def setUp(self):
        self.manager = create_user()
        self.store, _ = create_store(self.manager)
        self.client = authenticated_client(self.manager)

    def create_invitation(self, phone_number='09123334444', role='seller'):
        return self.client.post(
            '/api/v1/stores/invitations/',
            {'phone_number': phone_number, 'role': role},
            format='json',
        )

    def test_manager_can_create_list_and_revoke_invitation(self):
        response = self.create_invitation()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        invitation = StoreInvitation.objects.get(pk=response.data['id'])
        self.assertNotEqual(invitation.token_hash, response.data['token'])
        self.assertEqual(
            invitation.token_hash,
            hashlib.sha256(response.data['token'].encode()).hexdigest(),
        )

        list_response = self.client.get('/api/v1/stores/invitations/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertNotIn('token', list_response.data[0])

        delete_response = self.client.delete(
            f'/api/v1/stores/invitations/{invitation.id}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, StoreInvitation.StatusChoices.REVOKED)

    def test_new_invitation_revokes_previous_pending_invitation(self):
        first = self.create_invitation()
        second = self.create_invitation(role='admin')

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        first_invitation = StoreInvitation.objects.get(pk=first.data['id'])
        self.assertEqual(first_invitation.status, StoreInvitation.StatusChoices.REVOKED)
        self.assertEqual(
            StoreInvitation.objects.filter(
                store=self.store,
                phone_number='09123334444',
                status=StoreInvitation.StatusChoices.PENDING,
            ).count(),
            1,
        )

    def test_manager_role_cannot_be_invited(self):
        response = self.create_invitation(role='manager')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StoreInvitation.objects.exists())

    def test_seller_cannot_manage_invitations(self):
        seller = create_user()
        StoreMembership.objects.create(
            store=self.store,
            user=seller,
            role=StoreMembership.RoleChoices.SELLER,
        )
        response = authenticated_client(seller).post(
            '/api/v1/stores/invitations/',
            {'phone_number': '09123334444', 'role': 'seller'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_preview_masks_phone_and_does_not_reveal_account_state(self):
        response = self.create_invitation()
        preview = APIClient().get(
            f"/api/v1/stores/invitations/preview/{response.data['token']}/"
        )

        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data['store_name'], self.store.name)
        self.assertEqual(preview.data['masked_phone_number'], '0912***4444')
        self.assertNotIn('account_exists', preview.data)

    def test_new_user_registers_and_receives_tokens_membership_and_permissions(self):
        response = self.create_invitation(role='seller')
        token = response.data['token']

        registration = APIClient().post(
            f'/api/v1/stores/invitations/{token}/register/',
            {
                'username': 'invited-seller',
                'full_name': 'Invited Seller',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', registration.data)
        self.assertIn('refresh', registration.data)
        user = User.objects.get(username='invited-seller')
        membership = StoreMembership.objects.get(user=user)
        self.assertEqual(user.phone_number, '09123334444')
        self.assertEqual(membership.store, self.store)
        self.assertEqual(membership.role, StoreMembership.RoleChoices.SELLER)
        self.assertEqual(
            set(
                MembershipPermission.objects.filter(membership=membership)
                .values_list('permission__code', flat=True)
            ),
            {'create_sale', 'view_sales', 'view_inventory', 'view_dashboard'},
        )
        invitation = StoreInvitation.objects.get(pk=response.data['id'])
        self.assertEqual(invitation.status, StoreInvitation.StatusChoices.ACCEPTED)
        self.assertEqual(invitation.accepted_by, user)

    def test_existing_user_with_matching_phone_can_accept(self):
        user = create_user(phone_number='09123334444')
        response = self.create_invitation(role='admin')

        accepted = authenticated_client(user).post(
            f"/api/v1/stores/invitations/{response.data['token']}/accept/"
        )

        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        membership = StoreMembership.objects.get(user=user)
        self.assertEqual(membership.role, StoreMembership.RoleChoices.ADMIN)
        self.assertEqual(membership.store, self.store)

    def test_phone_mismatch_and_existing_membership_are_rejected(self):
        mismatch_user = create_user(phone_number='09120000000')
        response = self.create_invitation()
        mismatch = authenticated_client(mismatch_user).post(
            f"/api/v1/stores/invitations/{response.data['token']}/accept/"
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mismatch.data['code'], 'phone_mismatch')

        member = create_user(phone_number='09123334444')
        create_store(member)
        already_member = authenticated_client(member).post(
            f"/api/v1/stores/invitations/{response.data['token']}/accept/"
        )
        self.assertEqual(already_member.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(already_member.data['code'], 'already_member')

    def test_expired_revoked_used_and_invalid_links_are_rejected(self):
        expired_response = self.create_invitation(phone_number='09121110000')
        expired = StoreInvitation.objects.get(pk=expired_response.data['id'])
        expired.expires_at = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=['expires_at'])
        expired_preview = APIClient().get(
            f"/api/v1/stores/invitations/preview/{expired_response.data['token']}/"
        )
        self.assertEqual(expired_preview.data['code'], 'expired')

        revoked_response = self.create_invitation(phone_number='09122220000')
        self.client.delete(
            f"/api/v1/stores/invitations/{revoked_response.data['id']}/"
        )
        revoked_preview = APIClient().get(
            f"/api/v1/stores/invitations/preview/{revoked_response.data['token']}/"
        )
        self.assertEqual(revoked_preview.data['code'], 'revoked')

        user = create_user(phone_number='09123330000')
        used_response = self.create_invitation(phone_number=user.phone_number)
        authenticated_client(user).post(
            f"/api/v1/stores/invitations/{used_response.data['token']}/accept/"
        )
        used_again = authenticated_client(user).post(
            f"/api/v1/stores/invitations/{used_response.data['token']}/accept/"
        )
        self.assertEqual(used_again.data['code'], 'used')

        invalid = APIClient().get(
            '/api/v1/stores/invitations/preview/not-a-real-token/'
        )
        self.assertEqual(invalid.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(invalid.data['code'], 'invalid')

    def test_invitation_registration_rejects_existing_phone_and_rolls_back(self):
        create_user(phone_number='09123334444')
        response = self.create_invitation()
        registration = APIClient().post(
            f"/api/v1/stores/invitations/{response.data['token']}/register/",
            {
                'username': 'must-not-exist',
                'full_name': 'Existing Phone',
                'password': 'StrongPass123!',
            },
            format='json',
        )
        self.assertEqual(registration.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(registration.data['code'], 'account_exists')
        self.assertFalse(User.objects.filter(username='must-not-exist').exists())


class ConcurrentInvitationAcceptanceTests(TransactionTestCase):
    reset_sequences = True

    def test_invitation_can_only_be_consumed_once(self):
        manager = create_user(username='concurrent-manager')
        store, manager_membership = create_store(manager)
        user = create_user(
            username='concurrent-seller',
            phone_number='09124445555',
        )
        response = authenticated_client(manager).post(
            '/api/v1/stores/invitations/',
            {'phone_number': user.phone_number, 'role': 'seller'},
            format='json',
        )
        token = response.data['token']

        def accept():
            close_old_connections()
            try:
                thread_user = User.objects.get(pk=user.pk)
                accept_store_invitation(token=token, user=thread_user)
                return 'accepted'
            except InvitationError as error:
                return error.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: accept(), range(2)))

        self.assertCountEqual(results, ['accepted', 'used'])
        self.assertEqual(
            StoreMembership.objects.filter(store=store, user=user).count(),
            1,
        )


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
