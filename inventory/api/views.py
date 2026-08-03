from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from catalog.models import ProductVariant
from inventory.services import create_inventory_movement
from inventory.api.serializers import InventoryMovementSerializer, InventorySerializer
from inventory.permissions import CanManageInventory, CanViewInventory
from stores.services import get_current_membership, MembershipResolutionError



class InventoryMovementCreateView(generics.CreateAPIView):

    serializer_class = InventoryMovementSerializer

    permission_classes = [IsAuthenticated, CanManageInventory]

    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error
        movement = create_inventory_movement(
            store=membership.store,
            variant=serializer.validated_data['variant'],
            quantity=serializer.validated_data['quantity'],
            movement_type=serializer.validated_data['movement_type'],
            user=self.request.user,
            note=serializer.validated_data.get('note', ''),
        )

        serializer.instance = movement



class InventoryListView(generics.ListAPIView):

    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, CanViewInventory]


    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return(
            ProductVariant.objects
            .filter(product__store_id=membership.store_id)
            .select_related('product')
        )