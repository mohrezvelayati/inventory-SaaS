from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.db.models import Q
from datetime import datetime

from wanted.api.serializers import WantedSerializer
from wanted.models import WantedProduct
from wanted.permissions import CanManageWanted
from wanted.services import create_wanted
from stores.services import get_current_membership, MembershipResolutionError



class WantedProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WantedSerializer
    permission_classes = [IsAuthenticated, CanManageWanted]
    lookup_url_kwarg = 'wanted_id'

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error
        return WantedProduct.objects.filter(store=membership.store)



class WantedListCreateView(generics.ListCreateAPIView):
    serializer_class = WantedSerializer
    permission_classes = [IsAuthenticated, CanManageWanted]


    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        wanted_products = WantedProduct.objects.filter(
            store=membership.store
        )

        search = self.request.query_params.get('search', '').strip()
        if search:
            wanted_products = wanted_products.filter(
                Q(product_name__icontains=search) |
                Q(brand__icontains=search) |
                Q(size__icontains=search)
            )

        min_count = self._parse_positive_integer(
            self.request.query_params.get('min_count'),
            'min_count',
        )
        product_id = self._parse_positive_integer(
            self.request.query_params.get('product_id'),
            'product_id',
        )
        date_from = self._parse_date(
            self.request.query_params.get('date_from'),
            'date_from',
        )
        date_to = self._parse_date(
            self.request.query_params.get('date_to'),
            'date_to',
        )

        if date_from and date_to and date_from > date_to:
            raise ValidationError({
                'date_to': 'date_to must be on or after date_from.'
            })

        if min_count:
            wanted_products = wanted_products.filter(wanted_count__gte=min_count)
        if product_id:
            wanted_products = wanted_products.filter(product_id=product_id)
        if date_from:
            wanted_products = wanted_products.filter(created_at__date__gte=date_from)
        if date_to:
            wanted_products = wanted_products.filter(created_at__date__lte=date_to)

        return wanted_products.order_by('id')

    @staticmethod
    def _parse_positive_integer(value, name):
        if not value:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError({name: 'A valid positive integer is required.'}) from error
        if parsed <= 0:
            raise ValidationError({name: 'A valid positive integer is required.'})
        return parsed

    @staticmethod
    def _parse_date(value, name):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as error:
            raise ValidationError({name: 'Date must use YYYY-MM-DD format.'}) from error
    

    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error
        wanted_product = create_wanted(
            store = membership.store,
            product = serializer.validated_data.get('product'),
            product_name=serializer.validated_data['product_name'],
            brand=serializer.validated_data.get('brand', ''),
            size = serializer.validated_data['size'],
            customer = serializer.validated_data.get('customer'),
            user = self.request.user
        )
        serializer.instance = wanted_product
