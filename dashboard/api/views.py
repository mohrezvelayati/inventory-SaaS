from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import Http404
from drf_spectacular.utils import extend_schema

from dashboard.api.serializers import (
    DashboardQuerySerializer,
    DashboardResponseSerializer,
    ReportQuerySerializer,
    ReportResponseSerializer,
)
from dashboard.cache import get_cached_dashboard, set_cached_dashboard
from dashboard.permissions import CanViewDashboard
from dashboard.services.sales import get_sales_overview
from dashboard.services.inventory import get_inventory_overview, get_low_stock_products
from dashboard.services.products import get_top_products
from dashboard.services.wanted import get_top_wanted
from dashboard.services.reports import get_store_report
from stores.services import get_current_membership, MembershipResolutionError


@extend_schema(
    tags=["dashboard"],
    description="داشبورد فروشگاه — نمایش خلاصه فروش، موجودی و محصولات پرفروش",
    parameters=[DashboardQuerySerializer],
    responses={200: DashboardResponseSerializer},
)
class DashboardView(APIView):

    permission_classes=[IsAuthenticated, CanViewDashboard]


    def get(self, request):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        store = membership.store

        query_serializer = DashboardQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)
        date_from = query_serializer.validated_data['date_from']
        date_to = query_serializer.validated_data['date_to']
        cached_data, cache_key = get_cached_dashboard(
            store_id=store.id,
            date_from=date_from,
            date_to=date_to,
        )

        if cached_data is not None:
            return Response(cached_data)


        data = {
            'sales': get_sales_overview(
                store=store,
                date_from=date_from,
                date_to=date_to,
            ),
            'inventory': get_inventory_overview(
                store=store,
            ),
            'low_stock': list(
                get_low_stock_products(
                    store=store,
                )
            ),
            'products': list(
                get_top_products(
                    store=store,
                    date_from=date_from,
                    date_to=date_to,
                )
            ),
            'wanted': list(
                get_top_wanted(
                    store=store,
                )
            ),
        }

        set_cached_dashboard(
            key=cache_key,
            data=data,
        )

        return Response(data)


@extend_schema(
    tags=['dashboard'],
    description='گزارش تحلیلی فروش و موجودی فروشگاه',
    parameters=[ReportQuerySerializer],
    responses={200: ReportResponseSerializer},
)
class ReportView(APIView):
    permission_classes = [IsAuthenticated, CanViewDashboard]

    def get(self, request):
        try:
            membership = get_current_membership(request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        report = get_store_report(
            store=membership.store,
            date_from=query.validated_data['date_from'],
            date_to=query.validated_data['date_to'],
        )
        return Response(ReportResponseSerializer(report).data)
