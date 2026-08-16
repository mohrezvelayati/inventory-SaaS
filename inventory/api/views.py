from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from datetime import datetime
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from inventory.models import InventoryMovement
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


class InventoryMovementHistoryView(generics.ListAPIView):

    serializer_class = InventoryMovementSerializer
    permission_classes = [IsAuthenticated, CanViewInventory]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        queryset = (
            InventoryMovement.objects
            .filter(variant__product__store_id=membership.store_id)
            .select_related('variant__product', 'created_by')
        )

        variant_id_value = self.request.query_params.get('variant_id')
        if variant_id_value is not None:
            try:
                variant_id_value = int(variant_id_value)
            except (ValueError, TypeError):
                raise ValidationError({'variant_id': 'A valid integer is required.'})
            queryset = queryset.filter(variant_id=variant_id_value)

        type_filter = self.request.query_params.get('type')
        if type_filter is not None:
            valid_types = [choice[0] for choice in InventoryMovement.MovementType.choices]
            if type_filter not in valid_types:
                raise ValidationError({
                    'type': 'Invalid movement type. Must be one of: ' + ', '.join(valid_types) + '.'
                })
            queryset = queryset.filter(movement_type=type_filter)

        date_from_value = self.request.query_params.get('date_from')
        date_to_value = self.request.query_params.get('date_to')

        date_from = self._parse_date(date_from_value, 'date_from')
        date_to = self._parse_date(date_to_value, 'date_to')

        if date_from and date_to and date_from > date_to:
            raise ValidationError({
                'date_to': 'date_to must be on or after date_from.'
            })

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by('-created_at', '-id')

    @staticmethod
    def _parse_date(value, name):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as error:
            raise ValidationError({
                name: 'Date must use YYYY-MM-DD format.'
            }) from error