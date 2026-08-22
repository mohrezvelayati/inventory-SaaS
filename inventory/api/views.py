from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.db.models import Q
from datetime import datetime
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from inventory.models import InventoryMovement
from inventory.services import create_inventory_movement
from inventory.api.serializers import (
    InventoryMovementCreateSerializer,
    InventoryMovementHistorySerializer,
    InventorySerializer,
)
from inventory.permissions import CanManageInventory, CanViewInventory
from stores.services import get_current_membership, MembershipResolutionError



class InventoryMovementCreateView(generics.CreateAPIView):

    serializer_class = InventoryMovementCreateSerializer

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

        inventory = (
            ProductVariant.objects
            .filter(product__store_id=membership.store_id)
            .select_related('product')
        )

        search = self.request.query_params.get('search', '').strip()
        if search:
            inventory = inventory.filter(
                Q(product__name__icontains=search) |
                Q(size__icontains=search)
            )

        return inventory.order_by('id')


class InventoryMovementHistoryView(generics.ListAPIView):

    serializer_class = InventoryMovementHistorySerializer
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

        product_id_value = self.request.query_params.get('product_id')
        if product_id_value is not None:
            product_id_value = self._parse_id(product_id_value, 'product_id')
            queryset = queryset.filter(variant__product_id=product_id_value)

        variant_id_value = self.request.query_params.get('variant_id')
        if variant_id_value is not None:
            variant_id_value = self._parse_id(variant_id_value, 'variant_id')
            queryset = queryset.filter(variant_id=variant_id_value)

        created_by_id_value = self.request.query_params.get('created_by_id')
        if created_by_id_value is not None:
            created_by_id_value = self._parse_id(
                created_by_id_value,
                'created_by_id',
            )
            queryset = queryset.filter(created_by_id=created_by_id_value)

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
    def _parse_id(value, name):
        try:
            parsed_value = int(value)
        except (ValueError, TypeError) as error:
            raise ValidationError({
                name: 'A valid positive integer is required.'
            }) from error

        if parsed_value <= 0:
            raise ValidationError({
                name: 'A valid positive integer is required.'
            })

        return parsed_value

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
