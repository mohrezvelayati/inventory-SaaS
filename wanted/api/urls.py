from django.urls import path


from wanted.api.views import WantedListCreateView, WantedProductDetailView


urlpatterns = [
    path('', WantedListCreateView.as_view()),
    path('<int:wanted_id>/', WantedProductDetailView.as_view()),

]