from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.utils import timezone


from dashboard.services.sales import get_sales_overview
from dashboard.services.inventory import get_inventory_overview, get_low_stock_products
from dashboard.services.products import get_top_products
from dashboard.services.wanted import get_top_wanted




class DashboardView(APIView):

    permission_classes=[
        IsAuthenticated
    ]


    def get(self, request):

        membership = (request.user.memberships.first())


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