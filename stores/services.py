import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError


from stores.models import (
    MembershipPermission,
    Permission,
    Store,
    StoreInvitation,
    StoreMembership,
)
from users.models import User


ROLE_PERMISSIONS = {
    StoreMembership.RoleChoices.MANAGER: [
        'manage_catalog', 'view_inventory', 'manage_inventory',
        'create_sale', 'view_sales', 'manage_customers',
        'manage_wanted', 'view_dashboard', 'manage_members',
    ],
    StoreMembership.RoleChoices.SELLER: [
        'create_sale', 'view_sales', 'view_inventory', 'view_dashboard',
    ],
    StoreMembership.RoleChoices.ADMIN: [
        'create_sale', 'view_sales', 'view_inventory', 'view_dashboard',
        'manage_wanted',
    ],
}

def assign_default_permissions(*, membership):
    role_permissions = ROLE_PERMISSIONS.get(membership.role, [])
    for code in role_permissions:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={'name': code.replace('_', ' ').title()},
        )
        MembershipPermission.objects.get_or_create(
            membership=membership, permission=permission
        )




class MembershipResolutionError(Exception):
    """Base error for resolving a user's single store membership."""


class NoMembershipError(MembershipResolutionError):
    """Raised when a user does not belong to a store."""


class MultipleMembershipsError(MembershipResolutionError):
    """Raised when a user belongs to more than one store."""


def get_current_membership(user):
    """
    Return the user's only store membership.
    """
    try:
        return user.memberships.select_related("store").get()
    except StoreMembership.DoesNotExist as error:
        raise NoMembershipError from error
    except StoreMembership.MultipleObjectsReturned as error:
        raise MultipleMembershipsError from error


@transaction.atomic
def create_store_with_membership(*, user, name):

    store = Store.objects.create(name=name)

    membership = StoreMembership.objects.create(store=store, user=user, role=StoreMembership.RoleChoices.MANAGER)
    assign_default_permissions(membership=membership)

    return store


@transaction.atomic
def create_store_membership(*, store, user, role):

    membership = StoreMembership.objects.create(store=store, user=user, role=role)
    assign_default_permissions(membership=membership)

    return membership


class InvitationError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def hash_invitation_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def normalize_phone_number(phone_number):
    return phone_number.strip()


def validate_invitation(invitation):
    if invitation.status == StoreInvitation.StatusChoices.ACCEPTED:
        raise InvitationError('used', 'This invitation has already been used.')
    if invitation.status == StoreInvitation.StatusChoices.REVOKED:
        raise InvitationError('revoked', 'This invitation has been revoked.')
    if invitation.expires_at <= timezone.now():
        raise InvitationError('expired', 'This invitation has expired.')
    return invitation


def get_invitation_by_token(token, *, lock=False):
    queryset = StoreInvitation.objects.select_related('store')
    if lock:
        queryset = queryset.select_for_update()
    try:
        invitation = queryset.get(token_hash=hash_invitation_token(token))
    except StoreInvitation.DoesNotExist as error:
        raise InvitationError('invalid', 'This invitation is invalid.') from error
    return validate_invitation(invitation)


@transaction.atomic
def create_store_invitation(*, actor_membership, phone_number, role):
    if actor_membership.role != StoreMembership.RoleChoices.MANAGER:
        raise ValidationError({'detail': 'Only managers can invite members.'})
    if role not in (
        StoreMembership.RoleChoices.SELLER,
        StoreMembership.RoleChoices.ADMIN,
    ):
        raise ValidationError({'role': 'Only seller and admin roles can be invited.'})

    phone_number = normalize_phone_number(phone_number)
    Store.objects.select_for_update().get(pk=actor_membership.store_id)
    now = timezone.now()
    StoreInvitation.objects.filter(
        store_id=actor_membership.store_id,
        phone_number=phone_number,
        status=StoreInvitation.StatusChoices.PENDING,
    ).update(
        status=StoreInvitation.StatusChoices.REVOKED,
        revoked_at=now,
        updated_at=now,
    )

    raw_token = secrets.token_urlsafe(32)
    invitation = StoreInvitation.objects.create(
        store_id=actor_membership.store_id,
        invited_by_id=actor_membership.user_id,
        phone_number=phone_number,
        role=role,
        token_hash=hash_invitation_token(raw_token),
        expires_at=now + timedelta(days=7),
    )
    return invitation, raw_token


@transaction.atomic
def revoke_store_invitation(*, actor_membership, invitation):
    locked_invitation = StoreInvitation.objects.select_for_update().get(
        pk=invitation.pk,
        store_id=actor_membership.store_id,
    )
    if locked_invitation.status != StoreInvitation.StatusChoices.PENDING:
        raise ValidationError({'detail': 'Only pending invitations can be revoked.'})
    locked_invitation.status = StoreInvitation.StatusChoices.REVOKED
    locked_invitation.revoked_at = timezone.now()
    locked_invitation.save(update_fields=['status', 'revoked_at', 'updated_at'])


def _consume_invitation(*, invitation, user):
    membership = create_store_membership(
        store=invitation.store,
        user=user,
        role=invitation.role,
    )
    invitation.status = StoreInvitation.StatusChoices.ACCEPTED
    invitation.accepted_by = user
    invitation.accepted_at = timezone.now()
    invitation.save(
        update_fields=['status', 'accepted_by', 'accepted_at', 'updated_at']
    )
    return membership


@transaction.atomic
def accept_store_invitation(*, token, user):
    invitation = get_invitation_by_token(token, lock=True)
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if normalize_phone_number(locked_user.phone_number) != invitation.phone_number:
        raise InvitationError(
            'phone_mismatch',
            'The account phone number does not match this invitation.',
        )
    if StoreMembership.objects.filter(user=locked_user).exists():
        raise InvitationError(
            'already_member',
            'This account already belongs to a store.',
        )
    return _consume_invitation(invitation=invitation, user=locked_user)


@transaction.atomic
def register_with_store_invitation(*, token, user_data):
    invitation = get_invitation_by_token(token, lock=True)
    if User.objects.filter(phone_number=invitation.phone_number).exists():
        raise InvitationError(
            'account_exists',
            'An account with this phone number already exists. Please log in.',
        )
    try:
        user = User.objects.create_user(
            phone_number=invitation.phone_number,
            **user_data,
        )
    except IntegrityError as error:
        raise InvitationError(
            'account_exists',
            'An account with this phone number already exists. Please log in.',
        ) from error
    membership = _consume_invitation(invitation=invitation, user=user)
    return user, membership


def get_user_stores(user):
    return get_current_membership(user).store


@transaction.atomic
def update_store_membership_role(*, actor_membership, membership, role):
    if membership.store_id != actor_membership.store_id:
        raise ValidationError({'membership': 'Membership not found'})

    if role not in StoreMembership.RoleChoices.values:
        raise ValidationError({'role': 'Invalid role'})

    Store.objects.select_for_update().get(id=actor_membership.store_id)

    locked_membership = StoreMembership.objects.select_for_update().get(pk=membership.pk)

    if locked_membership.user_id == actor_membership.user_id:
        raise ValidationError({'role': 'You cannot change your own role'})

    if (
        locked_membership.role == StoreMembership.RoleChoices.MANAGER
        and role != StoreMembership.RoleChoices.MANAGER
        and StoreMembership.objects.filter(
            store_id=actor_membership.store_id,
            role=StoreMembership.RoleChoices.MANAGER
        ).count() == 1
    ):
        raise ValidationError({'role': 'Cannot remove the last manager from the store'})

    locked_membership.role = role
    locked_membership.save(
        update_fields=['role', 'updated_at']
    )
    assign_default_permissions(membership=locked_membership)
    return locked_membership



@transaction.atomic
def delete_store_membership(*, actor_membership, membership):
    if membership.store_id != actor_membership.store_id:
        raise ValidationError({'membership': 'Membership not found'})

    Store.objects.select_for_update().get(id=actor_membership.store_id)

    locked_membership = StoreMembership.objects.select_for_update().get(pk=membership.pk)

    if locked_membership.user_id == actor_membership.user_id:
        raise ValidationError({'membership': 'You cannot remove yourself from the store'})

    if (
        locked_membership.role == StoreMembership.RoleChoices.MANAGER
        and StoreMembership.objects.filter(
            store_id=actor_membership.store_id,
            role=StoreMembership.RoleChoices.MANAGER
        ).count() == 1
    ):
        raise ValidationError({'membership': 'Cannot remove the last manager from the store'})


    locked_membership.delete()



def assign_membership_permission(*, actor_membership, membership, permission):
    if membership.store_id != actor_membership.store_id:
        raise ValidationError(
            {'membership' : 'Membership Not Found.'}
        )

    if membership.user_id == actor_membership.user_id:
        raise ValidationError(
            {'membership' : 'You cannot change your own permissions.'}
        )

    membership_permission, created = (
        MembershipPermission.objects.get_or_create(
            membership=membership,
            permission=permission,
        )
    )

    if not created:
        raise ValidationError(
            {'permission' : 'This permission is already assigned'}
        )
    return membership_permission



def revoke_membership_permission(*, actor_membership, membership_permission):
    target_membership = membership_permission.membership

    if target_membership.store_id != actor_membership.store_id:
        raise ValidationError(
            {'membership' : 'Membership not found'}
        )

    if target_membership.user_id == actor_membership.user_id:
        raise ValidationError(
            {'membership' : 'You cannot change your own permissions.'}
        )
    membership_permission.delete()
