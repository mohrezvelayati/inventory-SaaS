from django.urls import path


from dashboard.api.views import DashboardView, ReportView


urlpatterns = [
    path('', DashboardView.as_view()),
    path('reports/', ReportView.as_view()),
]
