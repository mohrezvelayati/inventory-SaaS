from logging import exception
from django.db import transaction

from stores.models import Store, StoreMembership


@transaction.atomic
def create_store_with_membership(*, user, name):

    store = Store.objects.create(name=name)

    StoreMembership.objects.create(store=store, user=user, role=StoreMembership.RoleChoices.MANAGER)

    return store


def create_store_membership(*, store, user, role):

    membership = StoreMembership.objects.create(store=store, user=user, role=role)

    return membership


def get_user_stores(user):
    #
    memberships = StoreMembership.objects.first()

    if not memberships:
        raise exception("User is not a member of any store.")
    
    return memberships.store