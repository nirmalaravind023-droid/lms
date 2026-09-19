"""Custom login backend.

Connection flow:
- Login form sends one identifier field called `username`
- Django calls this backend during authentication
- This backend checks whether that value matches email, username, or phone
"""
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailUsernamePhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # The login screen uses one box, so we treat the same value as email/username/phone.
        identifier = (username or kwargs.get("email") or "").strip()
        if not identifier or not password:
            return None

        user = (
            User.objects.filter(
                Q(email__iexact=identifier)
                | Q(username__iexact=identifier)
                | Q(phone_number__iexact=identifier)
            )
            .distinct()
            .first()
        )
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
