from django.urls import path


from wanted.api.views import WantedListCreateView


urlpatterns = [
    path('', WantedListCreateView.as_view()),
]