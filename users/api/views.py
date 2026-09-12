from django.conf import settings
from django.http import Http404
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import OpenApiResponse, extend_schema


from users.models import User
from users.api.serializers import (
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserSerializer,
)
from users.services import (
    PasswordResetError,
    change_password,
    confirm_password_reset,
    request_password_reset,
)
from stores.demo import refresh_demo_timeline
from stores.services import MembershipResolutionError



@extend_schema(auth=[])
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_register'


class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_login'


class DemoUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The demo account is temporarily unavailable.'
    default_code = 'demo_unavailable'


@extend_schema(
    auth=[],
    request=None,
    responses={
        200: TokenPairSerializer,
        404: OpenApiResponse(description='Demo mode is disabled'),
        503: OpenApiResponse(description='Demo account is unavailable'),
    },
)
class DemoLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'demo_login'

    def post(self, request):
        if not settings.DEMO_MODE_ENABLED:
            raise Http404

        try:
            user = User.objects.get(is_demo=True, is_active=True)
            refresh_demo_timeline(user=user)
        except (User.DoesNotExist, MembershipResolutionError) as error:
            raise DemoUnavailable from error

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MeView(generics.RetrieveUpdateAPIView):
    """
    This view is for retrieving the currently authenticated user's information
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(auth=[], request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_password(user=request.user, **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',', 1)[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(
        auth=[],
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(description='Request accepted')},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_password_reset(
                phone_number=serializer.validated_data['phone_number'],
                requester_ip=_client_ip(request),
            )
        except PasswordResetError as exc:
            return Response(
                {'code': exc.code, 'detail': 'Too many requests. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={'Retry-After': '3600'},
            )
        return Response(
            {'detail': 'If an account matches, a reset code will be sent.'},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(auth=[], request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(**serializer.validated_data)
        except PasswordResetError as exc:
            return Response(
                {'code': exc.code, 'detail': 'The reset code is invalid or unavailable.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
