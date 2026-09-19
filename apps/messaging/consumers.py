from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Conversation, ConversationParticipant, Message

MAX_CHAT_MESSAGE_LENGTH = 2000
CHAT_RATE_LIMIT = 20
CHAT_RATE_WINDOW_SECONDS = 60


def parse_chat_payload(text_data: str) -> tuple[bool, str, str]:
    try:
        payload = json.loads(text_data)
    except json.JSONDecodeError:
        return False, "", "Invalid message payload."
    body = str(payload.get("message", "")).strip()
    if not body:
        return False, "", ""
    if len(body) > MAX_CHAT_MESSAGE_LENGTH:
        return False, "", "Message is too long."
    return True, body, ""


@dataclass
class MessageRateLimiter:
    limit: int = CHAT_RATE_LIMIT
    window_seconds: int = CHAT_RATE_WINDOW_SECONDS
    timestamps: list[float] = field(default_factory=list)

    def allow(self, *, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now
        window_start = current_time - self.window_seconds
        self.timestamps = [item for item in self.timestamps if item > window_start]
        if len(self.timestamps) >= self.limit:
            return False
        self.timestamps.append(current_time)
        return True


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        self.message_rate_limiter = MessageRateLimiter()

        if not await self.user_can_join():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.mark_as_read()
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        valid, body, error = parse_chat_payload(text_data)
        if error:
            await self.send(text_data=json.dumps({"error": error}))
            return
        if not valid:
            return
        if not self.message_rate_limiter.allow():
            await self.send(text_data=json.dumps({"error": "Message rate limit exceeded."}))
            return

        message = await self.create_message(body)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": {
                    "sender": self.scope["user"].get_full_name() or self.scope["user"].email,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def user_can_join(self) -> bool:
        user = self.scope["user"]
        return user.is_authenticated and Conversation.objects.filter(
            id=self.conversation_id,
            participants__user=user,
        ).exists()

    @database_sync_to_async
    def create_message(self, body: str) -> Message:
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(conversation=conversation, sender=self.scope["user"], body=body)
        ConversationParticipant.objects.filter(conversation=conversation, user=self.scope["user"]).update(last_read_at=timezone.now())
        return message

    @database_sync_to_async
    def mark_as_read(self) -> None:
        ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.scope["user"],
        ).update(last_read_at=timezone.now())
