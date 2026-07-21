from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response


from sales.api.serializers import SaleCreateSerializer, SaleSerializer, SaleItemCreateSerializer
from sales.services import create_sale, add_sale_item, complete_sale
from sales.models import Sale



class SaleCreateView(CreateAPIView):

    serializer_class = SaleCreateSerializer
    permission_classes = [IsAuthenticated]


    def perform_create(self, serializer):
        membership = self.request.user.memberships.first()

        sale = create_sale(
            store=membership.store,
            seller=membership,
            customer=serializer.validated_data.get('customer'),
            channel=serializer.validated_data.get('channel'),
            payment_method=serializer.validated_data.get('payment_method'),
        )

        serializer.instance = sale




class SaleItemCreateView(
    generics.CreateAPIView
):

    serializer_class = SaleItemCreateSerializer

    permission_classes = [
        IsAuthenticated
    ]


    def perform_create(self, serializer):

        sale = Sale.objects.get(
            id=self.kwargs["sale_id"]
        )


        add_sale_item(
            sale=sale,
            variant=serializer.validated_data["variant"],
            quantity=serializer.validated_data["quantity"],
            discount=serializer.validated_data.get(
                "discount",
                0
            )
        )



class SaleCompleteView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    def post(self,request,sale_id):

        sale = Sale.objects.get(id=sale_id)
        membership = (request.user.memberships.first())
        complete_sale(sale=sale,user=request.user)

        return Response(
            {
                "message":
                "Sale completed successfully"
            },
            status=status.HTTP_200_OK
        )
    



class SaleListView(generics.ListAPIView):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Sale.objects.filter(
            store__memberships__user=self.request.user
        ).prefetch_related("items")