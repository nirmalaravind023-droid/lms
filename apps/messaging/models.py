"""Messaging data models.

Structure:
- Conversation = one thread
- ConversationParticipant = which users belong to the thread
- Message = each chat/email-like entry inside the thread
"""
from django.db import models

from apps.common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    company = models.ForeignKey("organizations.Company", related_name="conversations", on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    is_direct = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "updated_at"], name="msg_conv_company_updated_idx"),
        ]

    def __str__(self) -> str:
        return self.title or f"Conversation {self.id}"


class ConversationParticipant(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, related_name="participants", on_delete=models.CASCADE)
    user = models.ForeignKey("accounts.User", related_name="conversation_memberships", on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("conversation", "user")
        indexes = [
            models.Index(fields=["user", "last_read_at"], name="msg_part_user_read_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.conversation_id}"


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey("accounts.User", related_name="sent_messages", on_delete=models.CASCADE)
    body = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="msg_message_conv_created_idx"),
            models.Index(fields=["sender", "created_at"], name="msg_message_sender_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sender}: {self.body[:40]}"
