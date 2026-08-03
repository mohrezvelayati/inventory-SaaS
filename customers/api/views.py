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

        return Customer.objects.filter(store=membership.store)


    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error
        serializer.save(store=membership.store)