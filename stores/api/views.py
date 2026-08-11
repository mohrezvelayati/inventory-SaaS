from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.shortcuts import get_object_or_404

from stores.permissions import CanManageMembers
from stores.models import StoreMembership, Permission, MembershipPermission
from stores.api.serializers import (
    StoreSerializer,
    MembershipSerializer,
    MembershipRoleUpdateSerializer,
    MembershipPermissionSerializer,
    PermissionSerializer,
    )
from stores.services import (
    MembershipResolutionError,
    assign_membership_permission,
    create_store_membership,
    create_store_with_membership,
    delete_store_membership,
    get_current_membership,
    revoke_membership_permission,
    update_store_membership_role,
    )





class StoreCreateView(generics.CreateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        
        store = create_store_with_membership(
            user=self.request.user,
            name=serializer.validated_data['name']
        )
        serializer.instance = store


class MembershipListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404('You do not belong to any store')

        return StoreMembership.objects.filter(store=membership.store)

    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404('You do not belong to any store')

        new_membership = create_store_membership(
            store=membership.store,
            user=serializer.validated_data["user"],
            role=serializer.validated_data["role"],
        )

        serializer.instance = new_membership


class MembershipDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, CanManageMembers]
    lookup_url_kwarg = 'membership_id'
    http_method_names = [
        'get',
        'patch',
        'delete',
        'head',
        'options',
    ]

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

    def get_queryset(self):
        actor_membership = self.get_actor_membership()
        return StoreMembership.objects.filter(
            store_id=actor_membership.store_id
        )

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return MembershipRoleUpdateSerializer
        return MembershipSerializer

    def perform_update(self, serializer):
        updated_membership = update_store_membership_role(
            actor_membership=self.get_actor_membership(),
            membership=serializer.instance,
            role=serializer.validated_data['role'],
        )
        serializer.instance = updated_membership

    def perform_destroy(self, instance):
        delete_store_membership(
            actor_membership=self.get_actor_membership(),
            membership=instance,
    )


class PermissionListView(generics.ListAPIView):
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_queryset(self):
        return Permission.objects.order_by('code')


class MembershipPermissionListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipPermissionSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found') from error

    def get_target_membership(self):
        actor_membership = self.get_actor_membership()

        return get_object_or_404(
            StoreMembership,
            pk=self.kwargs['membership_id'],
            store_id=actor_membership.store_id,
        )

    def get_queryset(self):
        return (
            MembershipPermission.objects.filter(
            membership=self.get_target_membership()
        )
        .select_related('permission')
        .order_by('id')
        )

    def perform_create(self, serializer):
        membership_permission = assign_membership_permission(
            actor_membership=self.get_actor_membership(),
            membership=self.get_target_membership(),
            permission=serializer.validated_data['permission'],
        )
        serializer.instance = membership_permission


class MembershipPermissionDetailView(generics.DestroyAPIView):
    serializer_class = MembershipPermissionSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]
    lookup_url_kwarg = 'membership_permission_id'

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

    def get_queryset(self):
        actor_membership = self.get_actor_membership()
        return (
            MembershipPermission.objects
            .filter(
                membership_id = self.kwargs['membership_id'],
                membership__store_id = actor_membership.store_id,
            )
            .select_related('membership')
        )
    def perform_destroy(self, instance):
        revoke_membership_permission(
            actor_membership=self.get_actor_membership(),
            membership_permission=instance,
        )