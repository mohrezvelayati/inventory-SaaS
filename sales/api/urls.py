from django.urls import path

from sales.api.views import (
    SaleCreateView,
    SaleItemCreateView,
    SaleCompleteView,
    SaleListView,
)


urlpatterns = [

    path("",SaleListView.as_view()),
    path("create/",SaleCreateView.as_view()),
    path("<int:sale_id>/items/",SaleItemCreateView.as_view()),
    path("<int:sale_id>/complete/",SaleCompleteView.as_view()),

]