import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class LiveClassConsumer(AsyncWebsocketConsumer):
    """
    WebRTC Signaling Server via WebSockets.
    Handles: offer, answer, ice-candidate, chat messages, participant events.
    """

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'live_{self.room_code}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Access control: verify enrollment for students at WebSocket connect
        if self.user.role == 'student':
            is_enrolled = await self.check_enrollment()
            if not is_enrolled:
                await self.close()
                return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Record participation
        await self.record_join()

        # Announce to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant_join',
                'user_id': str(self.user.pk),
                'user_name': self.user.full_name,
                'role': self.user.role,
                'channel_name': self.channel_name,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.record_leave()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participant_leave',
                    'user_id': str(self.user.pk),
                    'user_name': self.user.full_name,
                }
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'signal_type': 'offer',
                    'sdp': data.get('sdp'),
                    'sender_id': str(self.user.pk),
                    'target_id': data.get('target_id'),
                }
            )
        elif msg_type == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'signal_type': 'answer',
                    'sdp': data.get('sdp'),
                    'sender_id': str(self.user.pk),
                    'target_id': data.get('target_id'),
                }
            )
        elif msg_type == 'ice-candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'signal_type': 'ice-candidate',
                    'candidate': data.get('candidate'),
                    'sender_id': str(self.user.pk),
                    'target_id': data.get('target_id'),
                }
            )
        elif msg_type == 'chat':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'live_chat_message',
                    'content': data.get('content', ''),
                    'sender_id': str(self.user.pk),
                    'sender_name': self.user.full_name,
                    'timestamp': timezone.now().strftime('%H:%M'),
                }
            )

    async def webrtc_signal(self, event):
        target_id = event.get('target_id')
        # Send to all (target filtering happens client-side)
        await self.send(text_data=json.dumps({
            'type': event['signal_type'],
            'sdp': event.get('sdp'),
            'candidate': event.get('candidate'),
            'sender_id': event['sender_id'],
            'target_id': target_id,
        }))

    async def participant_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'role': event['role'],
        }))

    async def participant_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_left',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        }))

    async def live_chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def record_join(self):
        from .models import LiveSession, SessionParticipant
        try:
            session = LiveSession.objects.get(room_code=self.room_code, is_active=True)
            SessionParticipant.objects.get_or_create(session=session, user=self.user)
        except LiveSession.DoesNotExist:
            pass

    @database_sync_to_async
    def record_leave(self):
        from .models import LiveSession, SessionParticipant
        try:
            session = LiveSession.objects.get(room_code=self.room_code)
            SessionParticipant.objects.filter(
                session=session, user=self.user, left_at__isnull=True
            ).update(left_at=timezone.now())
        except LiveSession.DoesNotExist:
            pass

    @database_sync_to_async
    def check_enrollment(self):
        from .models import LiveSession
        from apps.courses.models import Enrollment
        try:
            session = LiveSession.objects.get(room_code=self.room_code)
            if not session.course:
                return True
            # For educators (creator or assigned sub-educator), enrollment doesn't apply
            if self.user.role == 'educator':
                return True
            return Enrollment.objects.filter(
                student=self.user,
                course=session.course,
                payment_status='paid'
            ).exists()
        except LiveSession.DoesNotExist:
            return False
