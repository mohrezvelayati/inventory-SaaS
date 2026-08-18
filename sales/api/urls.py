from django.urls import path

from sales.api.views import (
    SaleCancelView,
    SaleCompleteView,
    SaleCreateView,
    SaleDetailView,
    SaleItemCreateView,
    SaleItemDetailView,
    SaleListView,
)

urlpatterns = [

    path("",SaleListView.as_view()),
    path("create/",SaleCreateView.as_view()),
    path("<int:sale_id>/", SaleDetailView.as_view()),
    path("<int:sale_id>/items/",SaleItemCreateView.as_view()),
    path('<int:sale_id>/items/<int:item_id>/',SaleItemDetailView.as_view()),
    path("<int:sale_id>/complete/",SaleCompleteView.as_view()),
    path("<int:sale_id>/cancel/",SaleCancelView.as_view()),

]