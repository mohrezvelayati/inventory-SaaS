from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from django.shortcuts import get_object_or_404


from sales.api.serializers import SaleCreateSerializer, SaleSerializer, SaleItemCreateSerializer
from sales.services import create_sale, add_sale_item, complete_sale
from sales.models import Sale
from stores.services import get_current_membership, MembershipResolutionError



class SaleCreateView(CreateAPIView):

    serializer_class = SaleCreateSerializer
    permission_classes = [IsAuthenticated]


    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        sale = create_sale(
            store=membership.store,
            seller=membership,
            customer=serializer.validated_data.get('customer'),
            channel=serializer.validated_data['channel'],
            payment_method=serializer.validated_data.get('payment_method'),
        )

        serializer.instance = sale




class SaleItemCreateView(generics.CreateAPIView):

    serializer_class = SaleItemCreateSerializer

    permission_classes = [IsAuthenticated]


    def perform_create(self, serializer):

        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404("Sale not found.")

        sale = get_object_or_404(
            Sale.objects.select_related("store"),
            id=self.kwargs["sale_id"],
            store=membership.store,
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

    permission_classes = [IsAuthenticated]


    def post(self, request, sale_id):

        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError:
            raise Http404("Sale not found.")

        sale = get_object_or_404(
            Sale.objects.select_related("store"),
            id=sale_id,
            store=membership.store,
        )

        complete_sale(sale=sale, user=request.user)

        return Response(
            {"message": "Sale completed successfully"},
            status=status.HTTP_200_OK
        )
    

class SaleDetailView(generics.RetrieveAPIView):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request, sale_id):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        sale = get_object_or_404(
            Sale.objects.select_related("store"),
            id=sale_id,
            store=membership.store,
        )

        return sale



class SaleListView(generics.ListAPIView):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Sale.objects.filter(
            store=membership.store
        ).prefetch_related('items')
