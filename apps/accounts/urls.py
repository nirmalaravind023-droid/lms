"""URL routes for registration and the user directory."""
from django.urls import path

from .views import (
    RegistrationSuccessView,
    RegistrationView,
    UserDetailView,
    UserDirectoryView,
    UserLifecycleActionView,
    UserLifecycleRequestCreateView,
    UserLifecycleRequestDecisionView,
    UserTransferView,
)


urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("register/success/", RegistrationSuccessView.as_view(), name="register-success"),
    path("lifecycle/request/", UserLifecycleRequestCreateView.as_view(), name="user-lifecycle-request-create"),
    path("lifecycle/<uuid:user_id>/action/", UserLifecycleActionView.as_view(), name="user-lifecycle-action"),
    path("<uuid:user_id>/transfer/", UserTransferView.as_view(), name="user-transfer"),
    path("lifecycle/requests/<uuid:request_id>/decision/", UserLifecycleRequestDecisionView.as_view(), name="user-lifecycle-request-decision"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("", UserDirectoryView.as_view(), name="user-directory"),
]
