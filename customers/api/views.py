from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from customers.models import Customer
from customers.api.serializers import CustomerSerializer
from stores.services import get_current_membership, MembershipResolutionError
from customers.permissions import CanManageCustomers


class CustomerListCreateView(generics.ListCreateAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, CanManageCustomers]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Customer.objects.filter(
            store=membership.store
        ).order_by('id')


    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error
        serializer.save(store=membership.store)



class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, CanManageCustomers]
    lookup_url_kwarg = 'customer_id'


    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Customer.objects.filter(store_id=membership.store_id)
