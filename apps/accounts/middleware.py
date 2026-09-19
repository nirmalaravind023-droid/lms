from django.contrib import messages
from django.shortcuts import redirect


class DeveloperAdminOnlyMiddleware:
    """Keep Django's /admin/ console limited to developer-side admin roles."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and request.user.is_authenticated:
            if not getattr(request.user, "can_access_django_admin", False):
                messages.info(
                    request,
                    "Django admin is reserved for Developer Admin and Platform Admin accounts. Use the LMS workspace for HR tasks.",
                )
                return redirect("dashboard-home")
        return self.get_response(request)
