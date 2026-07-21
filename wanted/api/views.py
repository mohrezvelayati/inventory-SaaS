from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


from wanted.api.serializers import WantedSerializer
from wanted.models import WantedProduct
from wanted.services import create_wanted




class WantedListCreateView(generics.ListCreateAPIView):
    serializer_class = WantedSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        return WantedProduct.objects.filter(
            store__memberships__user=self.request.user
        )
    

    def perform_create(self, serializer):
        membership = (self.request.user.memberships.first())
        wanted_product = create_wanted(
            store = membership.store,
            product = serializer.validated_data.get('product'),
            product_name=serializer.validated_data['product_name'],
            size = serializer.validated_data['size'],
            customer = serializer.validated_data.get('customer'),
            user = self.request.user
        )
        serializer.instance = wanted_product