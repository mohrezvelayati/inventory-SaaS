from django.urls import path


from dashboard.api.views import DashboardView


urlpatterns = [
    path('', DashboardView.as_view())
]