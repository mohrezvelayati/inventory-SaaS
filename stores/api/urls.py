from django.urls import path
from stores.api.views import (
    StoreCreateView,
    CurrentStoreDetailView,
    MembershipListCreateView,
    MembershipDetailView,
    PermissionListView,
    MembershipPermissionListCreateView,
    MembershipPermissionDetailView,
    StoreInvitationAcceptView,
    StoreInvitationDestroyView,
    StoreInvitationListCreateView,
    StoreInvitationPreviewView,
    StoreInvitationRegisterView,
    )



urlpatterns = [
    path('', StoreCreateView.as_view(), name='store-create'),
    path('current/', CurrentStoreDetailView.as_view(), name='store-current-detail'),
    path('members/', MembershipListCreateView.as_view(), name='membership-list-create'),
    path(
        'invitations/',
        StoreInvitationListCreateView.as_view(),
        name='store-invitation-list-create',
    ),
    path(
        'invitations/preview/<str:token>/',
        StoreInvitationPreviewView.as_view(),
        name='store-invitation-preview',
    ),
    path(
        'invitations/<int:invitation_id>/',
        StoreInvitationDestroyView.as_view(),
        name='store-invitation-destroy',
    ),
    path(
        'invitations/<str:token>/register/',
        StoreInvitationRegisterView.as_view(),
        name='store-invitation-register',
    ),
    path(
        'invitations/<str:token>/accept/',
        StoreInvitationAcceptView.as_view(),
        name='store-invitation-accept',
    ),
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
