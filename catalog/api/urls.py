from django.urls import path, include


from catalog.api.views import CategoryListCreateView, ProductListCreateView, ProductVariantCreateView



urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('product/<int:product_id>/variants/', ProductVariantCreateView.as_view(), name='variant-create')
]