from django.urls import path

from customers.api.views import CustomerListCreateView, CustomerDetailView


urlpatterns = [
    path('', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('<int:customer_id>/', CustomerDetailView.as_view(), name='customer-detail'),
]