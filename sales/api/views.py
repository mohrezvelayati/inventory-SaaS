from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from django.shortcuts import get_object_or_404
from datetime import datetime
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema


from sales.api.serializers import (
    SaleCreateSerializer,
    SaleItemCreateSerializer,
    SaleItemUpdateSerializer,
    SaleSerializer,
)
from sales.services import (
    add_sale_item,
    cancel_sale,
    complete_sale,
    create_sale,
    delete_sale_item,
    update_sale_item,
)
from sales.models import Sale, SaleItem
from stores.services import get_current_membership, MembershipResolutionError
from sales.permissions import CanCreateSale, CanViewSales



class SaleCreateView(CreateAPIView):

    serializer_class = SaleCreateSerializer
    permission_classes = [IsAuthenticated, CanCreateSale]


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
            payment_method=serializer.validated_data['payment_method'],
        )

        serializer.instance = sale




class SaleItemCreateView(generics.CreateAPIView):

    serializer_class = SaleItemCreateSerializer

    permission_classes = [IsAuthenticated, CanCreateSale]


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


        sale_item = add_sale_item(
            sale=sale,
            variant=serializer.validated_data["variant"],
            quantity=serializer.validated_data["quantity"],
            discount=serializer.validated_data.get("discount",0)
        )
        serializer.instance = sale_item



@extend_schema(
    tags=["sales"],
    description="تکمیل یک فاکتور (تغییر وضعیت به completed)",
    methods=["POST"],
    request=None,
    responses={
        200: {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        }
    },
)


class SaleItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SaleItemUpdateSerializer
    permission_classes = [IsAuthenticated, CanCreateSale]
    lookup_url_kwarg = 'item_id'

    http_method_names = [
        'patch',
        'delete',
        'head',
        'options',
    ]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Sale item not found.') from error

        return (
            SaleItem.objects
            .filter(
                sale_id=self.kwargs['sale_id'],
                sale__store_id=membership.store_id,
            )
            .select_related(
                'sale',
                'variant__product',
            )
        )

    def perform_update(self, serializer):
        updated_sale_item = update_sale_item(
            sale_item=serializer.instance,
            quantity=serializer.validated_data.get('quantity'),
            discount=serializer.validated_data.get('discount'),
        )

        serializer.instance = updated_sale_item

    def perform_destroy(self, instance):
        delete_sale_item(sale_item=instance)


class SaleCompleteView(APIView):

    permission_classes = [IsAuthenticated, CanCreateSale]


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
    permission_classes = [IsAuthenticated, CanViewSales]
    lookup_url_kwarg = 'sale_id'

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return (
            Sale.objects
            .filter(store=membership.store)
            .prefetch_related('items__variant__product')
        )



class SaleListView(generics.ListAPIView):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, CanViewSales]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404("Store Not Found") from error

        sales = Sale.objects.filter(store=membership.store)

        status_filter = self.request.query_params.get("status")
        channel_filter = self.request.query_params.get("channel")
        date_from_value = self.request.query_params.get("date_from")
        date_to_value = self.request.query_params.get("date_to")

        if status_filter:
            if status_filter not in Sale.StatusChoices.values:
                raise ValidationError({"status": "Invalid sale status."})

            sales = sales.filter(status=status_filter)

        if channel_filter:
            if channel_filter not in Sale.ChannelChoices.values:
                raise ValidationError({"channel": "Invalid sale channel."})

            sales = sales.filter(channel=channel_filter)

        date_from = self.parse_date_parameter(
            name="date_from",
            value=date_from_value,
        )
        date_to = self.parse_date_parameter(
            name="date_to",
            value=date_to_value,
        )

        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_to": "date_to must be on or after date_from."})

        if date_from:
            sales = sales.filter(created_at__date__gte=date_from)

        if date_to:
            sales = sales.filter(created_at__date__lte=date_to)

        return (
            sales
            .prefetch_related("items__variant__product")
            .order_by("-created_at", "-id")
        )

    @staticmethod
    def parse_date_parameter(name, value):
        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as error:
            raise ValidationError({
                name: "Date must use YYYY-MM-DD format."
            }) from error


@extend_schema(
    tags=["sales"],
    description="لغو یک فاکتور (تغییر وضعیت به cancelled)",
    methods=["POST"],
    request=None,
    responses={
        200: {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        }
    },
)
class SaleCancelView(APIView):
    permission_classes = [IsAuthenticated, CanCreateSale]

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

        cancel_sale(sale=sale, user=request.user)

        return Response(
            {"message": "Sale canceled successfully"},
            status=status.HTTP_200_OK
        )