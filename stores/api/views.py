from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from stores.permissions import CanManageMembers
from stores.models import StoreMembership
from stores.api.serializers import StoreSerializer, MembershipSerializer, MembershipRoleUpdateSerializer
from stores.services import (
    MembershipResolutionError,
    create_store_membership,
    create_store_with_membership,
    get_current_membership,
    update_store_membership_role,
    delete_store_membership,
)





class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        
        store = create_store_with_membership(
            user=self.request.user,
            name=serializer.validated_data['name']
        )
        serializer.instance = store


class MembershipListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404('You do not belong to any store')

        return StoreMembership.objects.filter(store=membership.store)

    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404('You do not belong to any store')

        new_membership = create_store_membership(
        store=membership.store,
        user=serializer.validated_data["user"],
        role=serializer.validated_data["role"],
        )

        serializer.instance = new_membership


class MembershipDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, CanManageMembers]
    lookup_url_kwarg = 'membership_id'
    http_method_names = [
        'get',
        'patch',
        'delete',
        'head',
        'options',
    ]

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

    def get_queryset(self):
        actor_membership = self.get_actor_membership()
        return StoreMembership.objects.filter(
            store_id=actor_membership.store_id
        )

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return MembershipRoleUpdateSerializer
        return MembershipSerializer

    def perform_update(self, serializer):
        updated_membership = update_store_membership_role(
            actor_membership=self.get_actor_membership(),
            membership=serializer.instance,
            role=serializer.validated_data['role'],
        )
        serializer.instance = updated_membership

    def perform_destroy(self, instance):
        delete_store_membership(
            actor_membership=self.get_actore_membership(),
            membership=instance,
        )