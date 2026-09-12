from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.api.views import (
    DemoLoginView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)
from config.health import LiveView, ReadyView




urlpatterns = [
    path('api/v1/health/live/', LiveView.as_view(), name='health-live'),
    path('api/v1/health/ready/', ReadyView.as_view(), name='health-ready'),
    path('admin/', admin.site.urls),

    # User-related endpoints
    path('api/v1/users/', include('users.api.urls')),

    # Token authentication endpoints
    path('api/v1/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/demo/', DemoLoginView.as_view(), name='demo_login'),
    path('api/v1/auth/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/v1/auth/password/change/', PasswordChangeView.as_view(), name='password-change'),
    path(
        'api/v1/auth/password-reset/request/',
        PasswordResetRequestView.as_view(),
        name='password-reset-request',
    ),
    path(
        'api/v1/auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),

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

    # Customers app endpoints
    path('api/v1/customers/', include('customers.api.urls')),

    # Wanted app endpoints
    path('api/v1/wanted/', include('wanted.api.urls')),


    # Dashboard app endpoints
    path('api/v1/dashboard/', include('dashboard.api.urls')),
]
