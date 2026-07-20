from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


from customers.models import Customer
from customers.api.serializers import CustomerSerializer




class CustomerListCreateView(generics.ListCreateAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(
            store__memberships__user=self.request.user
        )
    
    def perform_create(self, serializer):
        membership = self.request.user.memberships.first()

        serializer.save(
            store=membership.store
        )