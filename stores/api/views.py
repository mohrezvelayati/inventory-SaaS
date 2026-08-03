from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from stores.permissions import CanManageMembers
from stores.models import StoreMembership
from stores.api.serializers import StoreSerializer, MembershipSerializer
from stores.services import create_store_with_membership, get_current_membership, MembershipResolutionError




class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        
        store = create_store_with_membership(
            user=self.request.user,
            name=serializer.validated_data['name']
        )
        serializer.instance = store



class StoreMembershipCreateView(generics.CreateAPIView):
    """
    This view is for creating a new membership for the currently authenticated user's store
    """
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        serializer.save(store=membership.store)


class MembershipListView(generics.ListAPIView):
    """
    This view is for listing all memberships of the currently authenticated user's store
    """
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return StoreMembership.objects.filter(store=membership.store)