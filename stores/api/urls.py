from django.urls import path
from stores.api.views import StoreCreateView, StoreMembershipCreateView, MembershipListView


urlpatterns = [
    path('', StoreCreateView.as_view(), name='store-create'),
    path('members', MembershipListView.as_view(), name='membership-list'),
    path('members/create', StoreMembershipCreateView.as_view(), name='store-membership-create')
]