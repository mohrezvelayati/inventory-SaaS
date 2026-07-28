from django.db import transaction

from stores.models import Store, StoreMembership


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
