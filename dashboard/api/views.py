from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import Http404
from drf_spectacular.utils import extend_schema


from django.utils import timezone


from dashboard.permissions import CanViewDashboard
from dashboard.services.sales import get_sales_overview
from dashboard.services.inventory import get_inventory_overview, get_low_stock_products
from dashboard.services.products import get_top_products
from dashboard.services.wanted import get_top_wanted
from stores.services import get_current_membership, MembershipResolutionError


@extend_schema(
    tags=["dashboard"],
    description="داشبورد فروشگاه — نمایش خلاصه فروش، موجودی و محصولات پرفروش",
    responses={
        200: {
            "type": "object",
            "properties": {
                "sales_overview": {
                    "type": "object",
                    "properties": {
                        "orders_count": {"type": "integer"},
                        "revenue": {"type": "integer"},
                        "discount": {"type": "integer"},
                    },
                },
                "inventory_overview": {
                    "type": "object",
                    "properties": {
                        "total_variants": {"type": "integer"},
                        "total_stock": {"type": "integer"},
                    },
                },
                "low_stock_products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product__name": {"type": "string"},
                            "size": {"type": "string"},
                            "current_stock": {"type": "integer"},
                        },
                    },
                },
                "top_products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "variant__product__name": {"type": "string"},
                            "sold_count": {"type": "integer"},
                        },
                    },
                },
                "top_wanted": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "size": {"type": "string"},
                            "wanted_count": {"type": "integer"},
                        },
                    },
                },
            },
        }
    },
)
class DashboardView(APIView):

    permission_classes=[IsAuthenticated, CanViewDashboard]


    def get(self, request):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        store = membership.store


        date_from = request.GET.get(
            "date_from",
            timezone.localdate()
        )


        date_to = request.GET.get(
            "date_to",
            timezone.localdate()
        )


        return Response({

            "sales":
            get_sales_overview(
                store=store,
                date_from=date_from,
                date_to=date_to
            ),


            "inventory":
            get_inventory_overview(
                store=store
            ),


            "low_stock":
            get_low_stock_products(
                store=store
            ),


            "products":
            get_top_products(
                store=store,
                date_from=date_from,
                date_to=date_to
            ),


            "wanted":
            get_top_wanted(
                store=store
            )

        })