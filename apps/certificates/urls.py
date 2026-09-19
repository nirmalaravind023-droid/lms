"""Certificate routes."""
from django.urls import path

from .views import CertificateListView


urlpatterns = [
    path("", CertificateListView.as_view(), name="certificate-list"),
]
