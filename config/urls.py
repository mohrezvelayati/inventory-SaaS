from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView




urlpatterns = [
    path('admin/', admin.site.urls),

    # User-related endpoints
    path('api/v1/users/', include('users.api.urls')),

    # Token authentication endpoints
    path('api/v1/auth/login/',TokenObtainPairView.as_view(),name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),

    # Swagger
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Stores app endpoints
    path('api/v1/stores/', include('stores.api.urls')),

    # Catalog app endpoints
    path('api/v1/catalog/', include('catalog.api.urls')),

    # Inventory app endpoints
    path('api/v1/inventory/', include('inventory.api.urls')),

    # Sales app endpoints
    path('api/v1/sales/', include('sales.api.urls')),
]
