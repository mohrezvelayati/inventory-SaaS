from django.urls import path, include


from catalog.api.views import (
    CategoryDetailView,
    CategoryListCreateView,
    ProductDetailView,
    ProductListCreateView,
    ProductSalePriceUpdateView,
    ProductVariantCreateView,
    ProductVariantDetailView,
    ProductVariantListView,
)

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:product_id>/', ProductDetailView.as_view()),
    path('variants/', ProductVariantListView.as_view(), name='variant-list'),
    path('products/<int:product_id>/prices/', ProductSalePriceUpdateView.as_view(), name='product-sale-price-update'),
    path('variants/<int:variant_id>/', ProductVariantDetailView.as_view()),
    path('product/<int:product_id>/variants/', ProductVariantCreateView.as_view(), name='variant-create'),
    path('categories/<int:category_id>/', CategoryDetailView.as_view(), name='category-detail'),
]