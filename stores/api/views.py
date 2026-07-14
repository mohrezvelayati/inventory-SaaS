from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from stores.permissions import CanCreateProduct
from stores.models import StoreMembership
from stores.api.serializers import StoreSerializer, MembershipSerializer
from stores.services import create_store_with_membership




class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        
        store = create_store_with_membership(user=self.request.user, name=serializer.validated_data['name'])
        serializer.instance = store



class StoreMembershipCreateView(generics.CreateAPIView):
    """
    This view is for creating a new membership for the currently authenticated user's store
    """
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]  # Only store managers can add new members

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.memberships.first().store)  # Assuming the user is a member of only one store for simplicity



class MembershipListView(generics.ListAPIView):
    """
    This view is for listing all memberships of the currently authenticated user's store
    """
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanCreateProduct]

    def get_queryset(self):
        membership = self.request.user.memberships.first()  # Assuming the user is a member of only one store for simplicity
        return StoreMembership.objects.filter(store=membership.store)