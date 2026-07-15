from django.urls import path

from sales.api.views import SaleCreateView



urlpatterns = [
    path('', SaleCreateView.as_view(), name='sale-create')
]