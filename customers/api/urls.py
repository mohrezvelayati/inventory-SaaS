from django.urls import path

from customers.api.views import CustomerListCreateView


urlpatterns = [
    path('', CustomerListCreateView.as_view())
]