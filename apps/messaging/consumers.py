from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Conversation, ConversationParticipant, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        if not await self.user_can_join():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.mark_as_read()
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data)
        body = payload.get("message", "").strip()
        if not body:
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
