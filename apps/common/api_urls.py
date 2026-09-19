from django.urls import path

from .views import GlobalSearchV1ApiView


app_name = "api_v1"

urlpatterns = [
    path("search/", GlobalSearchV1ApiView.as_view(), name="search"),
]
