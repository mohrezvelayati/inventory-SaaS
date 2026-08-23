from rest_framework.exceptions import ValidationError
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce

from customers.models import Customer
from customers.api.serializers import CustomerSerializer
from sales.models import Sale
from stores.services import get_current_membership, MembershipResolutionError
from customers.permissions import CanManageCustomers


class CustomerListCreateView(generics.ListCreateAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, CanManageCustomers]


    def _parse_positive_integer(self, value, param_name):
        if value is None or value == '':
            return None

        try:
            value = int(value)
        except ValueError:
            raise ValidationError({
                param_name: 'Must be an integer.'
            })

        if value < 0:
            raise ValidationError({
                param_name: 'Must be a positive integer.'
            })

        return value

    def _parse_gender(self, value):
        if value is None:
            return None

        if value not in Customer.GenderChoices.values:
            raise ValidationError({
                'gender': 'Must be one of: male, female.'
            })

        return value
    
    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        customers = Customer.objects.filter(store=membership.store)

        # Search 
        search = self.request.query_params.get('search', '').strip()
        if search:
            customers = customers.filter(
                Q(full_name__icontains=search) |
                Q(phone_number__icontains=search)
            )

        # Gender
        gender = self._parse_gender(
            self.request.query_params.get('gender')
        )

        if gender is not None:
            customers = customers.filter(gender=gender)

        # Age range
        age_min = self._parse_positive_integer(     
            self.request.query_params.get('age_min'), 'age_min'
        )
        age_max = self._parse_positive_integer(     
            self.request.query_params.get('age_max'), 'age_max'
        )

        if age_min is not None and age_max is not None and age_min > age_max:       
            raise ValidationError({'age_max': 'age_max must be on or after age_min.'})

        if age_min is not None:
            customers = customers.filter(age__gte=age_min)
        if age_max is not None:
            customers = customers.filter(age__lte=age_max)

        # Total quantitythis customer bought
        customers = customers.annotate(
            total_items_purchased=Coalesce(
                Sum(
                    'sales__items__quantity',
                    filter=Q(sales__status=Sale.StatusChoices.COMPLETED),
                    distinct=True,
                ),
                0,
            )
        )


        return customers.order_by('id')


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
