from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated


from sales.api.serializers import SaleCreateSerializer
from sales.services import create_sale
from sales.permissions import CanCreateSale



class SaleCreateView(CreateAPIView):

    serializer_class = SaleCreateSerializer
    permission_classes = [IsAuthenticated, CanCreateSale]


    def perform_create(self, serializer):
        membership = (self.request.user.memberships.first())

        sale = create_sale(
            store=membership.store,
            seller=membership,
            customer_id=serializer.validated_data.get['customer'],
            channel=serializer.validated_data.get['channel'],
            payment_method=serializer.validated_data.get['payment_method'],
            items=serializer.validated_data['items']
        )

        serializer.instance = sale