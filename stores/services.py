from django.db import transaction
from rest_framework.exceptions import ValidationError


from stores.models import Store, StoreMembership, MembershipPermission


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

    StoreMembership.objects.create(store=store, user=user, role=StoreMembership.RoleChoices.MANAGER)

    return store


def create_store_membership(*, store, user, role):

    membership = StoreMembership.objects.create(store=store, user=user, role=role)

    return membership


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