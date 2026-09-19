from django.conf import settings


class SecurityHeadersMiddleware:
    """Adds security headers that are not built into Django settings."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_security_policy = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if content_security_policy:
            response.setdefault("Content-Security-Policy", content_security_policy)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
