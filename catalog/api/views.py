from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from stores.permissions import CanCreateProduct
from catalog.permissions import CanCreateVariant

from catalog.models import Category, Product
from catalog.api.serializers import CategorySerializer, ProductSerializer, ProductVariantSerializer
from catalog.services import create_category, create_product, create_variant




class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


    def get_queryset(self):
        # Return categories for the authenticated user's store
        return Category.objects.filter(store__memberships__user=self.request.user)
    


    def perform_create(self, serializer):
        # Create a new category for the authenticated user's store
        create_category(
            store=self.request.user.memberships.first().store, # Assuming the user has a store membership and we take the first one
            name=serializer.validated_data['name']
        )



class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, CanCreateProduct]  # Custom permission to check if the user can create products

    def get_queryset(self):
        # Return products for the authenticated user's store
        return Product.objects.filter(
        store__memberships__user=self.request.user
    )
    
    def perform_create(self, serializer):

        categories = serializer.validated_data.get('categories', [])

        product = create_product(
            store=self.request.user.memberships.first().store,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''), # get description if provided, else default to empty string
            categories=categories
        )
        
        serializer.instance = product  # Set the instance to the newly created product




class ProductVariantCreateView(generics.CreateAPIView):
    
    serializer_class = ProductVariantSerializer

    permission_classes = [
        IsAuthenticated,
        CanCreateVariant
    ]


    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']

        product = Product.objects.get(
            id=product_id,
            store__memberships__user=self.request.user
        )


        variant = create_variant(
            product=product,
            size=serializer.validated_data["size"],
            purchase_price=serializer.validated_data["purchase_price"],
            sale_price=serializer.validated_data["sale_price"],
        )

        serializer.instance = variant