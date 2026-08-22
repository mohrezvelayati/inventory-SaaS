from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema


from users.models import User
from users.api.serializers import RegisterSerializer, UserSerializer



@extend_schema(auth=[])
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


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
