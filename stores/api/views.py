from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404

from stores.permissions import CanManageMembers
from stores.models import (
    MembershipPermission,
    Permission,
    Store,
    StoreInvitation,
    StoreMembership,
)
from stores.api.serializers import (
    StoreSerializer,
    MembershipSerializer,
    MembershipRoleUpdateSerializer,
    MembershipPermissionSerializer,
    PermissionSerializer,
    InvitationRegistrationSerializer,
    InvitationPreviewSerializer,
    InvitationTokenSerializer,
    StoreInvitationSerializer,
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
    InvitationError,
    accept_store_invitation,
    create_store_invitation,
    get_invitation_by_token,
    register_with_store_invitation,
    revoke_store_invitation,
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


class CurrentStoreDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return get_object_or_404(Store, pk=membership.store_id)


class MembershipListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError:
            raise Http404('You do not belong to any store')

        return StoreMembership.objects.filter(
            store=membership.store
        ).select_related('user').order_by('id')

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


def invitation_error_response(error):
    error_status = (
        status.HTTP_404_NOT_FOUND
        if error.code == 'invalid'
        else status.HTTP_400_BAD_REQUEST
    )
    return Response(
        {'detail': error.message, 'code': error.code},
        status=error_status,
    )


def mask_phone_number(phone_number):
    if len(phone_number) < 7:
        return '***'
    return f'{phone_number[:4]}***{phone_number[-4:]}'


class StoreInvitationListCreateView(generics.ListCreateAPIView):
    serializer_class = StoreInvitationSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]
    pagination_class = None

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found') from error

    def get_queryset(self):
        membership = self.get_actor_membership()
        return StoreInvitation.objects.filter(
            store_id=membership.store_id,
            status=StoreInvitation.StatusChoices.PENDING,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at')

    def perform_create(self, serializer):
        invitation, raw_token = create_store_invitation(
            actor_membership=self.get_actor_membership(),
            phone_number=serializer.validated_data['phone_number'],
            role=serializer.validated_data['role'],
        )
        invitation.token = raw_token
        serializer.instance = invitation


class StoreInvitationDestroyView(generics.DestroyAPIView):
    serializer_class = StoreInvitationSerializer
    permission_classes = [IsAuthenticated, CanManageMembers]
    lookup_url_kwarg = 'invitation_id'

    def get_actor_membership(self):
        try:
            return get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found') from error

    def get_queryset(self):
        membership = self.get_actor_membership()
        return StoreInvitation.objects.filter(store_id=membership.store_id)

    def perform_destroy(self, instance):
        revoke_store_invitation(
            actor_membership=self.get_actor_membership(),
            invitation=instance,
        )


class StoreInvitationPreviewView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = InvitationPreviewSerializer

    @extend_schema(responses=InvitationPreviewSerializer)
    def get(self, request, token):
        try:
            invitation = get_invitation_by_token(token)
        except InvitationError as error:
            return invitation_error_response(error)
        return Response({
            'store_name': invitation.store.name,
            'role': invitation.role,
            'masked_phone_number': mask_phone_number(invitation.phone_number),
            'expires_at': invitation.expires_at,
        })


class StoreInvitationRegisterView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = InvitationRegistrationSerializer

    @extend_schema(responses={201: InvitationTokenSerializer})
    def post(self, request, token):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, _ = register_with_store_invitation(
                token=token,
                user_data=serializer.validated_data,
            )
        except InvitationError as error:
            return invitation_error_response(error)

        refresh = RefreshToken.for_user(user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class StoreInvitationAcceptView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MembershipSerializer

    @extend_schema(request=None, responses=MembershipSerializer)
    def post(self, request, token):
        try:
            membership = accept_store_invitation(token=token, user=request.user)
        except InvitationError as error:
            return invitation_error_response(error)
        return Response(MembershipSerializer(membership).data)
