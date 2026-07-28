from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.shortcuts import get_object_or_404

from catalog.permissions import CanCreateVariant
from catalog.models import Category, Product
from catalog.api.serializers import CategorySerializer, ProductSerializer, ProductVariantSerializer
from catalog.services import create_category, create_product, create_variant
from stores.permissions import CanCreateProduct
from stores.services import get_current_membership, MembershipResolutionError



class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Category.objects.filter(store=membership.store)
    


    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        category = create_category(
            store=membership.store,
            name=serializer.validated_data['name'],
        )
        serializer.instance = category



class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, CanCreateProduct]  # Custom permission to check if the user can create products

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Product.objects.filter(store=membership.store)

    
    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        categories = serializer.validated_data.get('categories', [])

        product = create_product(
            store=membership.store,
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
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        product = get_object_or_404(
            Product.objects.filter(store=membership.store),
            id=self.kwargs['product_id']
        )

        variant = create_variant(
            product=product,
            size=serializer.validated_data["size"],
            purchase_price=serializer.validated_data["purchase_price"],
            sale_price=serializer.validated_data["sale_price"],
        )

        serializer.instance = variant