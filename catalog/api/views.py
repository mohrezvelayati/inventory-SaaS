from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db.models import BigIntegerField, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError
from django.conf import settings

from catalog.permissions import CanManageCatalog
from catalog.models import Category, Product, ProductVariant
from catalog.api.serializers import CategorySerializer, ProductSerializer, ProductVariantSerializer
from catalog.services import create_category, create_product, create_variant, update_product, update_variant
from stores.services import get_current_membership, MembershipResolutionError



class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, CanManageCatalog]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        return Category.objects.filter(
            store=membership.store
        ).order_by('id')
    


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
    permission_classes = [IsAuthenticated, CanManageCatalog]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404("Store not found.") from error

        products = Product.objects.filter(store_id=membership.store_id)

        search = self.request.query_params.get("search")
        if search:
            products = products.filter(name__icontains=search)

        category_id = self.request.query_params.get('category_id')
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                raise ValidationError({"category_id": "Category ID must be an integer."})

            products = products.filter(category__id=category_id)


        stock_status = self.request.query_params.get("stock_status")

        if stock_status:
            allowed_statuses = {
                "in_stock",
                "low_stock",
                "out_of_stock",
            }

            if stock_status not in allowed_statuses:
                raise ValidationError({
                    "stock_status": "Invalid stock status."
                })

            products = products.annotate(
                total_stock=Coalesce(
                    Sum("variants__current_stock"),
                    Value(0),
                    output_field=BigIntegerField(),
                )
            )

            if stock_status == "out_of_stock":
                products = products.filter(total_stock=0)

            elif stock_status == "low_stock":
                products = products.filter(
                    total_stock__gt=0,
                    total_stock__lte=settings.LOW_STOCK_THRESHOLD,
                )

            else:
                products = products.filter(
                    total_stock__gt=settings.LOW_STOCK_THRESHOLD
                )

        return (
            products
            .prefetch_related("variants", "category")
            .order_by("id")
        )

    
    def perform_create(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store Not Found') from error

        categories = serializer.validated_data.get('category', [])

        product = create_product(
            store=membership.store,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''), # get description if provided, else default to empty string
            categories=categories
        )
        
        serializer.instance = product  # Set the instance to the newly created product


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, CanManageCatalog]
    lookup_url_kwarg = 'product_id'

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found.') from error
        return Product.objects.filter(store_id=membership.store_id).prefetch_related('variants', 'category')

    def perform_update(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found.') from error
        product = self.get_object()
        categories = serializer.validated_data.get('category', [])
        update_product(
            product=product,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            categories=categories,
        )
        serializer.instance = product


class ProductVariantCreateView(generics.CreateAPIView):
    
    serializer_class = ProductVariantSerializer

    permission_classes = [IsAuthenticated, CanManageCatalog]


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


class ProductVariantListView(generics.ListAPIView):
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, CanManageCatalog]

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found.') from error
        return (
            ProductVariant.objects
            .filter(product__store_id=membership.store_id)
            .select_related('product')
            .order_by('id')
        )


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, CanManageCatalog]
    lookup_url_kwarg = 'variant_id'

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found.') from error
        return ProductVariant.objects.filter(
            product__store_id=membership.store_id
        ).select_related('product')

    def perform_update(self, serializer):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404('Store not found.') from error
        variant = self.get_object()
        update_variant(
            variant=variant,
            size=serializer.validated_data['size'],
            purchase_price=serializer.validated_data['purchase_price'],
            sale_price=serializer.validated_data['sale_price'],
        )
        serializer.instance = variant




class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, CanManageCatalog]
    lookup_url_kwarg = "category_id"

    def get_queryset(self):
        try:
            membership = get_current_membership(self.request.user)
        except MembershipResolutionError as error:
            raise Http404("Store not found.") from error

        return Category.objects.filter(store_id=membership.store_id)
