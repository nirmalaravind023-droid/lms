from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.common.services import create_admin_audit_log


def _request_metadata(request) -> dict:
    if request is None:
        return {}
    return {
        "ip_address": request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0],
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "path": request.path,
    }


@receiver(user_logged_in)
def audit_user_logged_in(sender, request, user, **kwargs):
    create_admin_audit_log(
        action="auth_login",
        actor=user,
        entity_type="user",
        entity_id=str(user.id),
        metadata=_request_metadata(request),
    )


@receiver(user_logged_out)
def audit_user_logged_out(sender, request, user, **kwargs):
    if not user or not getattr(user, "is_authenticated", False):
        return
    create_admin_audit_log(
        action="auth_logout",
        actor=user,
        entity_type="user",
        entity_id=str(user.id),
        metadata=_request_metadata(request),
    )


@receiver(user_login_failed)
def audit_user_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get("username", "")
    create_admin_audit_log(
        action="auth_login_failed",
        actor=None,
        entity_type="user",
        entity_id="",
        metadata={
            **_request_metadata(request),
            "username": username,
        },
    )
