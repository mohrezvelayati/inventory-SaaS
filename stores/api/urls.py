from django.urls import path
from stores.api.views import StoreCreateView, MembershipListCreateView, MembershipDetailView


urlpatterns = [
    path('', StoreCreateView.as_view(), name='store-create'),
    path('members/', MembershipListCreateView.as_view(), name='membership-list-create'),
    path('members/<int:membership_id>/', MembershipDetailView.as_view(), name='membership-detail')
]