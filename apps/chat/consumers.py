import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user': self.user.full_name,
                'user_id': self.user.pk,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'user': self.user.full_name,
                    'user_id': self.user.pk,
                }
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if content:
                await self.save_message(content)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'content': content,
                        'sender': self.user.full_name,
                        'sender_id': self.user.pk,
                        'avatar': self.user.avatar.url if self.user.avatar else '',
                        'timestamp': timezone.now().strftime('%H:%M'),
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'content': event['content'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'avatar': event.get('avatar', ''),
            'timestamp': event['timestamp'],
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system',
            'content': f"{event['user']} joined the chat",
        }))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system',
            'content': f"{event['user']} left the chat",
        }))

    @database_sync_to_async
    def save_message(self, content):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            Message.objects.create(room=room, sender=self.user, content=content)
        except ChatRoom.DoesNotExist:
            pass
