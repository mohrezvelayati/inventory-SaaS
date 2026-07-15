from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from catalog.models import ProductVariant
from inventory.services import create_inventory_movement
from inventory.api.serializers import InventoryMovementSerializer, InventorySerializer
from inventory.permissions import CanViewInventory



class InventoryMovementCreateView(generics.CreateAPIView):

    serializer_class = InventoryMovementSerializer

    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        movement = create_inventory_movement(
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
        return ProductVariant.objects.filter(
            product__store__memberships__user=self.request.user
        )
