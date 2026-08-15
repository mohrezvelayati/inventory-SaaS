from django.urls import path, include


from catalog.api.views import CategoryListCreateView, ProductDetailView, ProductListCreateView, ProductVariantCreateView, CategoryDetailView, ProductVariantDetailView



urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:product_id>/', ProductDetailView.as_view()),
    path('variants/<int:variant_id>/', ProductVariantDetailView.as_view()),
    path('product/<int:product_id>/variants/', ProductVariantCreateView.as_view(), name='variant-create'),
    path('categories/<int:category_id>/', CategoryDetailView.as_view(), name='category-detail'),
]