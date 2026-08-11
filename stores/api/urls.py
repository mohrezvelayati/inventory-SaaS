from django.urls import path
from stores.api.views import (
    StoreCreateView,
    MembershipListCreateView,
    MembershipDetailView,
    PermissionListView,
    MembershipPermissionListCreateView,
    MembershipPermissionDetailView
    )



urlpatterns = [
    path('', StoreCreateView.as_view(), name='store-create'),
    path('members/', MembershipListCreateView.as_view(), name='membership-list-create'),
    path('members/<int:membership_id>/', MembershipDetailView.as_view(), name='membership-detail'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path(
        'members/<int:membership_id>/permissions/',
        MembershipPermissionListCreateView.as_view(),
        name='membership-permission-list-create',
    ),
    path(
    (
        'members/<int:membership_id>/permissions/'
        '<int:membership_permission_id>/'
    ),
        MembershipPermissionDetailView.as_view(),
        name='membership-permission-detail',
    ),
]