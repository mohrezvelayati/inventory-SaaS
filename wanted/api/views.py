from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.db.models import Q

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

        return wanted_products.order_by('id')
    

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
