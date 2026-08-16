from django.urls import path

from inventory.api.views import InventoryListView, InventoryMovementCreateView, InventoryMovementHistoryView



urlpatterns = [
    path('', InventoryListView.as_view(), name='inventory-list'),
    path('movements/create/', InventoryMovementCreateView.as_view(), name='inventory-movement-create'),
    path('movements/history/', InventoryMovementHistoryView.as_view(), name='inventory-movement-history'),
]