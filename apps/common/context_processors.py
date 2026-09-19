from django.db import models

FALLBACK_QUOTE = {
    "text": "The only thing we have to fear is fear itself.",
    "author": "Franklin D. Roosevelt",
}


def _sidebar_quote():
    try:
        from random_quotes_generator.quotes import get_random_quotes

        generated_quote = get_random_quotes()
    except Exception:
        return FALLBACK_QUOTE

    if " - " in generated_quote:
        text, author = generated_quote.rsplit(" - ", 1)
        return {
            "text": text.strip(),
            "author": author.strip(),
        }

    return {
        "text": generated_quote.strip(),
        "author": "Focus Today",
    }


def notification_counts(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "unread_course_notifications": 0,
            "unread_message_conversations": 0,
            "sidebar_quote": _sidebar_quote(),
        }

    from apps.courses.models import CourseNotification
    from apps.messaging.models import ConversationParticipant, Message
    from apps.accounts.models import UserLifecycleRequest

    pending_user_requests = 0
    if request.user.is_manager_like or request.user.is_admin_like:
        pending_requests = UserLifecycleRequest.objects.filter(status=UserLifecycleRequest.Status.PENDING)
        if request.user.company_id:
            pending_requests = pending_requests.filter(target_user__company=request.user.company)
        pending_user_requests = pending_requests.count()

    return {
        "unread_course_notifications": CourseNotification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count() + pending_user_requests,
        "unread_message_conversations": ConversationParticipant.objects.filter(
            user=request.user,
        ).exclude(
            conversation__messages__created_at__lte=models.F("last_read_at")
        ).filter(
            conversation__messages__isnull=False
        ).distinct().count(),
        "sidebar_quote": _sidebar_quote(),
    }
