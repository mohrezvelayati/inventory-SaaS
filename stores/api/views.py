from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from stores.permissions import CanManageMembers
from stores.models import StoreMembership
from stores.api.serializers import StoreSerializer, MembershipSerializer
from stores.services import (
    MembershipResolutionError,
    create_store_membership,
    create_store_with_membership,
    get_current_membership,
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

        create_store_membership(
            store=membership.store,
            user=serializer.validated_data['user'],
            role=serializer.validated_data['role']
        )