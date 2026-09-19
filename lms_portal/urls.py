"""Top-level URL map for the whole LMS.

Think of this file as the traffic controller:
- /users/ goes to account pages
- /courses/ goes to learning content
- /assessments/ goes to quizzes
- /messages/ goes to chat/inbox
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.decorators.cache import never_cache

from apps.accounts.forms import LMSAuthenticationForm
from apps.analytics.views import HomeDashboardView
from apps.common.views import GlobalSearchApiView


urlpatterns = [
    # Django admin is the built-in management console.
    path("admin/", admin.site.urls),
    # Custom login form is plugged into Django's standard LoginView.
    path(
        "accounts/login/",
        never_cache(auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=LMSAuthenticationForm,
        )),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("api/search/", GlobalSearchApiView.as_view(), name="global-search-api"),
    # The root route lands on the dashboard.
    path("", HomeDashboardView.as_view(), name="dashboard-home"),
    path("users/", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")),
    path("assessments/", include("apps.assessments.urls")),
    path("messages/", include("apps.messaging.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("certificates/", include("apps.certificates.urls")),
]

# Serve static assets locally even when DEBUG is false in the shell env.
# This uses Django's staticfiles finders so admin CSS/JS and project assets
# are both available under /static/.
urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
